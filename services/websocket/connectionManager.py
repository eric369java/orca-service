from fastapi import WebSocket

from services.websocket.protocols import ServerMessage

class ConnectionManager:
    def __init__(self):
        self.active_connections : dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    def disconnect(self, client_id: str) -> None:
        del self.active_connections[client_id]
        
    async def send_message(self, client_ids: list[str], message: ServerMessage) -> None:
        for client_id in client_ids:
            if client_id in self.active_connections:
                await self.active_connections[client_id].send_text(message.dump())