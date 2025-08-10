from enum import Enum

class RequestActions(Enum):
    GetActivity = "GET",
    CreateActivity = "POST",
    UpdateActivity = "PATCH"
    DeleteActivity = "DELETE"
    GetWeekOfActivities = "FULLWEEK"