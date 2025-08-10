from datetime import datetime, timedelta
from sqlmodel import Session, func, select
 
from database.models import Activity, ActivityDescription
from .requestActions import RequestActions
from ..websocket.responseStatus import ResponseStatus
from ..websocket.protocols import DescriptionResponse, ActivityResponse, Request, ResponseBase

class ScheduleService:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_response(self, schedule_id : str, request: Request) -> ResponseBase:
        if request.action not in [e.value for e in RequestActions]:
            return ResponseBase(status=ResponseStatus.INVALID, action=request.action, request_id=request.id)

        if request.action == RequestActions.GetWeekOfActivities:
            return self.get_activities(schedule_id=schedule_id, target_week=request.target_week)
        elif request.action == RequestActions.GetActivity:
            return self.get_activity(request)
        elif request.action == RequestActions.UpdateActivity:
            return self.update_activity(request)
        elif request.action == RequestActions.CreateActivity:
            return self.create_activity(request)
        elif request.action == RequestActions.DeleteActivity:
            return self.delete_activity(request)

    def get_activities(self, schedule_id: str, target_week: datetime) -> ActivityResponse:
        try:
            end_of_target_week = target_week + timedelta(weeks=1)
            activities_db = self.db_session.exec(select(Activity).where(Activity.schedule_id == schedule_id, \
                Activity.start >= target_week, Activity.end < end_of_target_week).order_by(Activity.start)).all()
        except:
            return ActivityResponse(status=ResponseStatus.SERVER_ERROR, action=RequestActions.GetWeekOfActivities, target_week=target_week)
        else: 
            return ActivityResponse(status=ResponseStatus.SUCCESS, action=RequestActions.GetWeekOfActivities, target_week=target_week, activities=activities_db)

    def get_activity(self, request: Request) -> DescriptionResponse:
        try: 
            activity_id = request.activity_id
            if not activity_id:
                return DescriptionResponse(status=ResponseStatus.INVALID, action=request.action, activity_id=activity_id, request_id=request.id)

            description_db = self.db_session.get(ActivityDescription, activity_id)
            if not description_db:
                return DescriptionResponse(status=ResponseStatus.NOT_FOUND, action=request.action, activity_id=activity_id, request_id=request.id)
        except:
            return DescriptionResponse(status=ResponseStatus.SERVER_ERROR, action=request.action, activity_id=activity_id, request_id=request.id)
        else:
            return DescriptionResponse(status=ResponseStatus.SUCCESS, action=request.action, activity_id=activity_id, \
                description=description_db.text, request_id=request.id)

    def create_activity(self, request: Request) -> ActivityResponse:
        try: 
            activity = request.activity
            if not activity: 
                return ActivityResponse(ResponseStatus.INVALID, action=request.action, target_week=request.target_week, request_id=request.id)

            if activity.start > activity.end or self.check_if_activity_overlaps_others(activity):
                return ActivityResponse(ResponseStatus.INVALID, action=request.action, target_week=request.target_week, request_id=request.id)
 
            # Add the activity
            self.db_session.add(activity)
            
            # Add the description
            if request.description:
                activity_description_db = ActivityDescription(activity_id=activity.id, text=request.description)
                self.db_session.add(activity_description_db)

            self.db_session.commit()
            self.db_session.refresh(activity)
        except:
            return ActivityResponse(status=ResponseStatus.SERVER_ERROR, action=request.action, target_week=request.target_week, request_id=request.id)
        else: 
            return ActivityResponse(status=ResponseStatus.SUCCESS, action=request.action, target_week=request.target_week, activities=[activity], request_id=request.id)

    def delete_activity(self, request: Request) -> ActivityResponse:
        try:
            if not request.activity_id:
                return ActivityResponse(status=ResponseStatus.INVALID, action=request.action, target_week=request.target_week, request_id=request.id)

            # Check if activity exists
            activity_db = self.db_session.get(Activity, request.activity.id)
            if not activity_db:
                return ActivityResponse(status=ResponseStatus.NOT_FOUND, action=request.action, target_week=request.target_week, request_id=request.id)

            self.db_session.delete(activity_db)
            self.db_session.commit()
        except:
            response = ActivityResponse(status=ResponseStatus.SERVER_ERROR, action=request.action, target_week=request.target_week, request_id=request.id)
            if activity_db:
                response.activities.append(activity_db)
            return response
        else:
            return ActivityResponse(status=ResponseStatus.SUCCESS, action=request.action, target_week=request.target_week, request_id=request.id)
    
    def update_activity(self, request: Request) -> ActivityResponse:
        try: 
            activity = request.activity
            if not activity or not activity.id: 
                return ActivityResponse(status=ResponseStatus.INVALID, action=request.action, target_week=request.target_week, request_id=request.id)

            activity_db = self.db_session.get(Activity, activity.id)
            if not activity_db:
                return ActivityResponse(status=ResponseStatus.NOT_FOUND, action=request.action, target_week=request.target_week, request_id=request.id)

            # Clients are responsible for incrementing the version each time they edit. If a client attempts to submit edit version n
            # but edit version m >= n was already processed, the request is discarded because edit version n was working with old values.
            # Successful edits are broadcasted, this is how clients know which version the activity is on.
            if activity_db.version >= activity.version:
                return ActivityResponse(status=ResponseStatus.EXPIRED, action=request.action, target_week=request.target_week, activities=[activity_db], request_id=request.id)

            if activity.start > activity.end or self.check_if_activity_overlaps_others(activity):
                return ActivityResponse(ResponseStatus.INVALID, action=request.action, target_week=request.target_week, activities=[activity_db], request_id=request.id)
            
            activity_db.sqlmodel_update(activity)
            self.db_session.add(activity_db)

            # Add the description
            if request.description:
                activity_description_db = ActivityDescription(activity_id=activity.id, text=request.description)
                self.db_session.add(activity_description_db)

            self.db_session.commit()
            self.db_session.refresh(activity_db)
        except:
            response = ActivityResponse(status=ResponseStatus.SERVER_ERROR, action=request.action, target_week=request.target_week, request_id=request.id)
            if activity_db:
                response.activities.append(activity_db)
            return response
        else: 
            return ActivityResponse(status=ResponseStatus.SUCCESS, action=request.action, target_week=request.target_week, activities=[activity_db], request_id=request.id)
    
    def check_if_activity_overlaps_others(self, activity: Activity) -> bool:
        collision_count = self.db_session.exec(select(func.count(Activity.id)).where(Activity.schedule_id == activity.schedule_id, \
            Activity.start < activity.end, Activity.end > activity.start, Activity.id != activity.id)).one()
        return collision_count > 0