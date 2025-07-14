from datetime import datetime, timedelta
from sqlmodel import Session, func, select, join
 
from database.models import Activity, ActivityDescription
from ..websocket.responseStatus import ResponseStatus
from ..websocket.protocols import ClientActivityMessage, ClientScheduleMessage, ServerMessage

ScheduleActions = ["CREATE", "DELETE", "STEP", "SWITCH"]
ActivityActions = ["GET", "POST", "PATCH", "DELETE"]

class ScheduleService:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_response_to_schedule_request(self, message: ClientScheduleMessage) -> ServerMessage:
        try:
            if message.action not in ScheduleActions:
                return ServerMessage(status=ResponseStatus.INVALID, message="Request contains an invalid action")
        except AttributeError:
            return ServerMessage(status=ResponseStatus.INVALID, message="Request missing action parameter")
        
        # TODO : Implement other actions
        if message.action == "STEP":
            return self.get_activities(message.schedule_id, message.current_week)
        else:
            return ServerMessage(status=ResponseStatus.INVALID, message="Request contains an invalid action")

    def get_response_to_activity_request(self, message: ClientActivityMessage) -> ServerMessage:
        try:
            if message.action not in ActivityActions:
                return ServerMessage(status=ResponseStatus.INVALID, message="Request contains an invalid action")
        except AttributeError:
            return ServerMessage(status=ResponseStatus.INVALID, message="Request missing action parameter")

        if message.action == "GET":
            return self.get_activity(message)
        elif message.action == "PATCH":
            return self.update_activity(message)
        elif message.action == "POST":
            return self.create_activity(message)
        elif message.action == "DELETE":
            return self.delete_activity(message)
        else:
            return ServerMessage(status=ResponseStatus.INVALID, message="Request contains an invalid action")
    
    def get_activities(self, schedule_id: str, current_week: datetime) -> ServerMessage:
        try:
            end_of_current_week = current_week + timedelta(weeks=1)
            activities = self.db_session.exec(select(Activity).where(Activity.schedule_id == schedule_id, \
                Activity.start >= current_week, Activity.end < end_of_current_week).order_by(Activity.start)).all()
        except:
            return ServerMessage(status=ResponseStatus.SERVER_ERROR, message="Could not get activities from schedule {}".format(schedule_id), current_week=current_week)
        else: 
            return ServerMessage(status=ResponseStatus.SUCCESS, current_week=current_week, payload=activities)
    
    def get_activity(self, message: ClientActivityMessage) -> ServerMessage:
        try: 
            activity_id = message.activity_id
            if not activity_id:
                return ServerMessage(status=ResponseStatus.INVALID, message="Missing activity id parameter")

            activity_db = self.db_session.exec(select(Activity, ActivityDescription).join(ActivityDescription))
            if not activity_db:
                return ServerMessage(status=ResponseStatus.NOT_FOUND, message="Activity with id {} not found".format(activity_id))
        except:
            return ServerMessage(status=ResponseStatus.SERVER_ERROR, message="Could not get activity with id {}".format(activity_id))
        else:
            return ServerMessage(status=ResponseStatus.SUCCESS, payload=activity_db)

    def create_activity(self, message: ClientActivityMessage) -> ServerMessage:
        try: 
            activity = message.activity
            if not activity: 
                return ServerMessage(ResponseStatus.INVALID, "No activity received")

            if activity.start > activity.end:
                return ServerMessage(ResponseStatus.INVALID, "Activity start time is later than the end time")

            if self.check_if_activity_overlaps_others(activity):
                return ServerMessage(ResponseStatus.INVALID, "New activity overlaps with another activity")
            
            # Add the activity
            self.db_session.add(activity)
            
            # Add the description
            if message.description:
                activity_description_db = ActivityDescription(activity_id=activity.id, text=message.description)
                self.db_session.add(activity_description_db)

            self.db_session.commit()
            self.db_session.refresh(activity)
        except:
            return ServerMessage(status=ResponseStatus.SERVER_ERROR, message="Could not create new activity")
        else: 
            return ServerMessage(status=ResponseStatus.SUCCESS, payload=activity)

    def delete_activity(self, message: ClientActivityMessage) -> ServerMessage:
        try:
            activity_id = message.activity_id
            if not activity_id:
                return ServerMessage(status=ResponseStatus.INVALID, message="Missing activity_id parameter".format(activity_id))

            # Check if activity exists
            activity_db = self.db_session.get(Activity, activity_id)
            if not activity_db:
                return ServerMessage(status=ResponseStatus.NOT_FOUND, message="Activity with id {} not found".format(activity_id))

            self.db_session.delete(activity_db)
            self.db_session.commit()
        except:
            return ServerMessage(status=ResponseStatus.SERVER_ERROR, message="Could not delete activity with id {}".format(activity_id))
        else:
            return ServerMessage(status=ResponseStatus.DISCARD, payload=activity_db)
    
    def update_activity(self, message: ClientActivityMessage) -> ServerMessage:
        try: 
            activity = message.activity
            if not activity or not activity.id: 
                return ServerMessage(ResponseStatus.INVALID, "No valid activity received")

            activity_db = self.db_session.get(Activity, activity.id)
            if not activity_db:
                return ServerMessage(status=ResponseStatus.NOT_FOUND, message="Activity with id {} not found".format(activity.id))

            if activity.start > activity.end:
                return ServerMessage(ResponseStatus.INVALID, "Activity start time is later than the end time")

            if self.check_if_activity_overlaps_others(activity):
                return ServerMessage(ResponseStatus.INVALID, "Activity's new time range overlaps with another activity")
            
            activity_db.sqlmodel_update(activity)
            self.db_session.add(activity_db)
            self.db_session.commit()
            self.db_session.refresh(activity_db)
        except:
            return ServerMessage(status=ResponseStatus.SERVER_ERROR, message="Could not apply updates to activity with id {}".format(activity.id))
        else: 
            return ServerMessage(status=ResponseStatus.SUCCESS, payload=activity_db)
    
    def check_if_activity_overlaps_others(self, activity: Activity) -> bool:
        collision_count = self.db_session.exec(select(func.count(Activity.id)).where(Activity.schedule_id == activity.schedule_id, \
            Activity.start < activity.end, Activity.end > activity.start)).one()
    
        return collision_count > 0