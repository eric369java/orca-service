from datetime import datetime, timedelta

def are_dates_in_same_week(date1: datetime, date2: datetime) -> bool:
    # TODO: Implement
    return True

def get_start_date_of_week(timestamp: datetime) -> datetime:
    weekday = datetime(timestamp.year, timestamp.month, timestamp.day)
    start_of_week = weekday - timedelta(days=weekday.weekday())
    
    return  start_of_week