import json
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from ..websocket.responseStatus import ResponseStatus
from ..websocket.protocols import Request, Response
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
    initial_activities = schedule_service.get_activities(schedule_id, websocket_manager.target_week[client_id])
    await websocket_manager.send_response([client_id], initial_activities)

    try:
        while True:
            client_data = await websocket.receive_text()      
            client_json = json.loads(client_data)
            response = None
            
            client_request = Request(client_json)
            if client_request.action == "GETWEEK":
                websocket_manager.update_client_target_week(client_request.client_id, client_request.target_week)

            response = schedule_service.get_response(schedule_id, client_request)
            if not response or response.status != ResponseStatus.SUCCESS:
                await websocket_manager.send_response([client_id], response)
            elif response.action == "GETWEEK":
                await websocket_manager.send_response([client_id], response)
            else:
                await websocket_manager.send_response_to_pool(schedule_id, response)
    except WebSocketDisconnect:
        websocket_manager.disconnect(client_id)

    