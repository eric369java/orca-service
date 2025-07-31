from datetime import datetime, timedelta

from fastapi import WebSocket
from sqlmodel import Session, select
from .utilities import are_dates_in_same_week, get_start_date_of_week
from ..websocket.connectionManager import ConnectionManager
from ..websocket.protocols import Response
from database.models import Schedule, ScheduleBookmark, Activity

class ScheduleConnectionManager(ConnectionManager):
    def __init__(self, db_session: Session):
        super().__init__()
        self.db_session = db_session
        self.client_schedule_connection = {}
        
        # The start of the week the user is on.
        self.target_week = {}

    async def connect(self, websocket: WebSocket, client_id: str, schedule_id: str) -> bool:
        await super().connect(websocket, client_id)

        # Connect the client to the schedule in order to get notifications
        self.client_schedule_connection[client_id] = schedule_id
  
        # Determine which week of the schedule the client was last on.
        week_start_db = self.db_session.exec(select(ScheduleBookmark.week_start).where(ScheduleBookmark.user_id == client_id, \
            ScheduleBookmark.schedule_id == schedule_id).limit(1)).one_or_none()
        
        if not week_start_db:
            # Determine the target_week from the earliest activity in the schedule
            earliest_start_db = self.db_session.exec(select(Activity.start).where(Activity.schedule_id == schedule_id) \
                .order_by(Activity.start).limit(1)).one_or_none()

            if not earliest_start_db:
                schedule_start_db = self.db_session.exec(select(Schedule.init_week_start).where(Schedule.id == schedule_id)).one_or_none()
                if not schedule_start_db:
                    return False
                else:
                    self.target_week[client_id] = get_start_date_of_week(schedule_start_db)
            else:
                self.target_week[client_id] = get_start_date_of_week(earliest_start_db)
        else:
            self.target_week[client_id] = week_start_db
        
        return True
    
    def disconnect(self, client_id: str) -> None:
        super().disconnect(client_id)
   
        # Save the week that the user was on before disconnecting
        schedule_id = self.client_schedule_connection[client_id]
        if schedule_id:
            schedule_bookmark_db = self.db_session.exec(select(ScheduleBookmark).where(ScheduleBookmark.user_id == client_id, \
                ScheduleBookmark.schedule_id == schedule_id)).one_or_none()
            
            if not schedule_bookmark_db:
                # Use the client's last known target_week's activities to determine timezone
                target_week = self.target_week[client_id]
                target_week_end = target_week + timedelta(weeks=1)
                time_zone_offset_db = self.db_session.exec(select(Activity.local_timezone).where(Activity.schedule_id == schedule_id, \
                    Activity.start > target_week, Activity.end < target_week_end).order_by(Activity.start).limit(1)).one_or_none()

                if not time_zone_offset_db:
                    time_zone_offset_db = self.db_session.exec(select(Schedule.init_timezone_offset).where(Schedule.id == schedule_id)).one()

                new_last_visited = ScheduleBookmark(user_id=client_id, schedule_id=schedule_id, week_start=target_week, week_start_timezone_offset=time_zone_offset_db)
                self.db_session.add(new_last_visited)
                self.db_session.commit()
            else:
                schedule_bookmark_db.week_start = self.target_week[client_id]
                self.db_session.add(schedule_bookmark_db)
                self.db_session.commit() 

        # Disconnect the client from the schedule
        del self.client_schedule_connection[client_id]
        del self.target_week[client_id]
    
    async def send_response_to_pool(self, schedule_id: str, response: Response):
        # Notify all clients that are connected to the schedule and are currently viewing the week
        # that's being updated
        for client_id, conn_schedule_id in self.client_schedule_connection.items():
            if conn_schedule_id == schedule_id and are_dates_in_same_week(response.target_week, self.target_week[client_id]):
                await self.active_connections[client_id].send_text(response.dump())

    def update_client_target_week(self, client_id: str, target_week: datetime):
        self.target_week[client_id] = target_week