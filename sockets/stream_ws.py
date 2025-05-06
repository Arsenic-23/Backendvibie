# sockets/stream_ws.py

from fastapi import WebSocket, WebSocketDisconnect
from database import connections, add_user_to_stream, remove_user_from_stream, get_users_in_stream
import json

async def stream_websocket_endpoint(websocket: WebSocket, stream_id: str, user_id: int, username: str):
    await websocket.accept()
    
    # Register connection
    connections[stream_id].append(websocket)
    add_user_to_stream(stream_id, {"user_id": user_id, "username": username})

    # Broadcast join event
    await broadcast(stream_id, {
        "event": "user_joined",
        "user": {"user_id": user_id, "username": username}
    })

    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        # Clean up on disconnect
        remove_user_from_stream(stream_id, user_id)
        connections[stream_id].remove(websocket)
        await broadcast(stream_id, {
            "event": "user_left",
            "user_id": user_id
        })

async def broadcast(stream_id: str, message: dict):
    dead_connections = []
    for connection in connections[stream_id]:
        try:
            await connection.send_text(json.dumps(message))
        except:
            dead_connections.append(connection)
    
    # Remove dead connections
    for dc in dead_connections:
        connections[stream_id].remove(dc)