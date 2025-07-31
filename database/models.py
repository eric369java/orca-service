import uuid as uuid_pkg
from datetime import datetime
from sqlmodel import Field, SQLModel

class UserData(SQLModel, table=True):
    id: uuid_pkg.UUID = Field(default_factory=uuid_pkg.uuid4, primary_key=True)
    preferred_currency: str = Field(default='USD', nullable=False)

class Schedule(SQLModel, table=True):
    id: uuid_pkg.UUID = Field(default_factory=uuid_pkg.uuid4, primary_key=True)
    init_week_start : datetime = Field(nullable=False)
    init_timezone_offset: int = Field(default=0, nullable=False)

class ScheduleBookmark(SQLModel, table=True):
    user_id: uuid_pkg.UUID = Field(nullable=False, primary_key=True, foreign_key='userdata.id')
    schedule_id: uuid_pkg.UUID = Field(nullable=False, primary_key=True, foreign_key='schedule.id')
    week_start: datetime = Field(nullable=False)
    week_start_timezone_offset: int = Field(default=0, nullable=False)

class Activity(SQLModel, table=True):
    id: uuid_pkg.UUID = Field(default_factory=uuid_pkg.uuid4, primary_key=True)
    schedule_id: uuid_pkg.UUID = Field(nullable=False, foreign_key='schedule.id')
    title: str = Field(nullable=False)
    type: str = Field(default='Default', nullable=False)
    cost: str | None = Field(nullable=True) # Numeric value and ISO 4217 code seperated by space. e.g. 100.00 USD
    start: datetime = Field(nullable=False)
    end: datetime = Field(nullable=False)
    location: str = Field(nullable=False)
    local_timezone: int = Field(default=0, nullable=False) # timezone +/- hours from UTC
    dest_location : str | None = Field(nullable=True) # only populated if type = transit.
    version : int = Field(nullable=False, default=0)

class ActivityDescription(SQLModel, table=True):
    activity_id: uuid_pkg.UUID = Field(nullable=False, primary_key=True, foreign_key='activity.id')
    text: str = Field(nullable=False)

class ScheduleAccess(SQLModel, table=True):
    schedule_id: uuid_pkg.UUID = Field(nullable=False, primary_key=True, foreign_key='schedule.id')
    owner_id: uuid_pkg.UUID = Field(nullable=False, primary_key=True, foreign_key='userdata.id')
    reciever_id: uuid_pkg.UUID = Field(nullable=False, primary_key=True, foreign_key='userdata.id')
    access_type: str = Field(default='Readonly', nullable=False)