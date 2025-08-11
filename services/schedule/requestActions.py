from enum import Enum

class RequestActions(str, Enum):
    GetActivity = "GET"
    CreateActivity = "POST"
    UpdateActivity = "PATCH"
    DeleteActivity = "DELETE"
    GetWeekOfActivities = "FULLWEEK"