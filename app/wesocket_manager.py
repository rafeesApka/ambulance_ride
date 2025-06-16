from fastapi import WebSocket
# app/websocket_manager.py
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, driver_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[driver_id] = websocket

    def disconnect(self, driver_id: int):
        self.active_connections.pop(driver_id, None)

    async def send_message(self, driver_id: int, message: dict):
        websocket = self.active_connections.get(driver_id)
        if websocket:
            await websocket.send_json(message)

manager = ConnectionManager()
