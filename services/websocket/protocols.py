import uuid as uuid_pkg
import json
from datetime import datetime
from database.models import Activity

class ResponseBase: 
    def __init__(self, status: int, action: str, request_id : str | None = None):
        self.status = status
        self.action = action
        self.request_id = request_id

    def dump(self):
        obj_dict = {
            "status" : self.status,
            "action" : self.action,
            "request_id" : self.request_id,
        }
        return json.dumps(obj_dict)

class ActivityResponse(ResponseBase):
    def __init__(self, status: int, action: str, target_week : datetime, activities : list[Activity] = [], request_id : str | None = None):
        super().__init__(status, action, request_id)
        self.target_week = target_week
        self.activities = activities

    def dump(self):
        obj_dict = {
            "status" : self.status,
            "action" : self.action,
            "target_week" : self.target_week.isoformat(),
            "request_id" : self.request_id,
        }

        activities = []
        for activity in self.activities:
            activities.append(activity.model_dump(mode='json'))
        obj_dict["activities"] = activities

        return json.dumps(obj_dict)

class DescriptionResponse(ResponseBase):
    def __init__(self, status : int, action : str, activity_id : str, description : str = '', request_id : str | None = None):
        super().__init__(status, action, request_id)
        self.activity_id = activity_id
        self.description = description

    def dump(self):
        obj_dict = {
            "status" : self.status,
            "action" : self.action,
            "request_id" : self.request_id,
            "activity_id" : self.activity_id,
            "description" : self.description
        }

        return json.dumps(obj_dict)

class Request:
    def __init__(self, json : dict):        
        self.id = json.get('id', None)
        self.client_id = json['client_id']
        self.action = json['action']
        self.target_week = datetime.fromisoformat(json['target_week'])
        self.activity_id = json.get('activity_id', None)
        self.description = json.get('description', None)

        activity_dict = json.get('activity', None)
        if activity_dict:    
            # Generate an id if there aren't any
            if 'id' not in activity_dict:
                id = uuid_pkg.uuid4()
                activity_dict.id = id
                self.activity_id = id
            
            # Manually convert non string fields
            activity_dict['local_timezone'] = int(activity_dict['local_timezone'])
            activity_dict['start'] = datetime.fromisoformat(activity_dict['start'])
            activity_dict['end'] = datetime.fromisoformat(activity_dict['end'])

            # Use the Pydantic model's __init__ function to create an instance from dict
            self.activity = Activity(**activity_dict)


