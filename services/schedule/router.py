import json
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from ..websocket.responseStatus import ResponseStatus
from ..websocket.protocols import ClientActivityMessageUtilities, ClientScheduleMessageUtilities
from database.database import get_session
from .scheduleService import ScheduleService
from .scheduleConnManager import ScheduleConnectionManager

router = APIRouter(prefix="/v1/schedule")

# TODO: Authentication
@router.websocket("/{schedule_id}/{client_id}")
async def schedule_websocket(websocket: WebSocket, schedule_id: str, client_id: str, db_session: Session = Depends(get_session)):
    websocket_manager = ScheduleConnectionManager(db_session)
    schedule_service = ScheduleService(db_session)
    
    await websocket_manager.connect(websocket, client_id, schedule_id)
    
    # Send the client the initial list of activities
    initial_activities = schedule_service.get_activities(schedule_id, websocket_manager.current_week[client_id])
    await websocket_manager.send_message([client_id], initial_activities)

    try:
        while True:
            client_data = await websocket.receive_text()      
            client_json = json.loads(client_data)
            response = None
            
            if client_json['type'] == "activity":
                client_message = ClientActivityMessageUtilities.deserialize(client_json)
                if client_message:
                    response = schedule_service.get_response_to_activity_request(client_message)
            elif client_json['type'] == "schedule":
                client_message = ClientScheduleMessageUtilities.deserialize(client_json)
                if client_message:
                    if client_message.action == "STEP":
                        websocket_manager.update_client_current_week(client_message.client_id, client_message.current_week)
                    response = schedule_service.get_response_to_schedule_request(client_message)

            if not response or response.status != ResponseStatus.SUCCESS:
                await websocket_manager.send_message([client_id], response)
            else:
                await websocket_manager.send_message_to_pool(schedule_id, response)
    except WebSocketDisconnect:
        websocket_manager.disconnect(client_id)

    