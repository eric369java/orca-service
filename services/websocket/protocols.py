import uuid as uuid_pkg
import json
from datetime import datetime
from database.models import Activity

class ServerMessage:
    def __init__(self, status: int, message: str | None = None, current_week: datetime | None = None, payload: Activity | list[Activity] | None = None):
        self.status = status
        self.message = message
        self.current_week = current_week 
        self.payload = payload
    
    def dump(self):
        obj_dict = {
            "status" : self.status.value,
            "message" : self.message,
        }

        if self.current_week:
            obj_dict["current_week"] = self.current_week.isoformat()

        if isinstance(self.payload, list):
            activities = []
            for activity in self.payload:
                activities.append(activity.model_dump(mode='json'))
            obj_dict["payload"] = activities
        elif isinstance(self.payload, Activity):
            obj_dict["payload"] = self.payload.model_dump(mode='json')
        else:
            obj_dict["payload"] = None

        return json.dumps(obj_dict)

class ClientMessage:
    def __init__(self, client_id: str, type: str):
        self.type = type
        self.client_id = client_id
        
class ClientActivityMessage(ClientMessage):
    def __init__(self, client_id: str, action: str, type: str = "activity", activity_id: str | None = None, activity: Activity | None = None, description: str | None = None):
        super().__init__(type, client_id)
        self.action = action
        self.activity_id = activity_id
        self.activity = activity
        self.description = description

class ClientScheduleMessage(ClientMessage):
    def __init__(self, client_id: str, action: str, schedule_id: str, current_week: datetime, type: str = "schedule"):
        super().__init__(type, client_id)
        self.action = action
        self.schedule_id = schedule_id
        self.current_week = current_week

class ClientScheduleMessageUtilities:
    @staticmethod
    def deserialize(json: dict) -> ClientScheduleMessage | None:
        try:
            current_week = datetime.fromisoformat(json['current_week'])
            client_schedule_message = ClientScheduleMessage(client_id=json['client_id'], action=json['action'],\
                schedule_id=json['schedule_id'], current_week=current_week, type=json['type'])
            return client_schedule_message
        except AttributeError:
            return None

class ClientActivityMessageUtilities:
    @staticmethod
    def deserialize(json: dict) -> ClientActivityMessage | None:
        try:
            client_activity_message = ClientActivityMessage(client_id=json['client_id'], action=json['action'], type='activity', description=json['description'])
        
            activity_dict = json['activity']
            if activity_dict:    
                
                # Generate an id if there aren't any
                if not activity_dict['id']:
                    id = uuid_pkg.uuid4()
                    activity_dict.id = id
                    client_activity_message.activity_id = id
                
                # Manually convert non string fields
                activity_dict['local_timezone'] = int(activity_dict['local_timezone'])
                activity_dict['start'] = datetime.fromisoformat(activity_dict['start'])
                activity_dict['end'] = datetime.fromisoformat(activity_dict['end'])

                # Use the Pydantic model's __init__ function to create an instance from dict
                client_activity_message.activity = Activity(activity_dict)
            return client_activity_message
        except AttributeError:
            return None
        except ValueError:
            return None

