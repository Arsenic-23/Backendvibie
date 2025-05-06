import json
from fastapi import WebSocket, WebSocketDisconnect
from database import (
    register_connection,
    unregister_connection,
    get_users_in_stream,
    get_connections,
    remove_user_from_stream
)

async def broadcast_user_list(stream_id: str):
    users = get_users_in_stream(stream_id)
    message = json.dumps({"event": "update_vibers", "users": users})
    for connection in get_connections(stream_id):
        try:
            await connection.send_text(message)
        except Exception:
            pass  # Ignore failed send

async def stream_websocket_endpoint(websocket: WebSocket, stream_id: str, user_id: int, username: str):
    await websocket.accept()
    register_connection(stream_id, websocket)
    await broadcast_user_list(stream_id)

    try:
        while True:
            await websocket.receive_text()  # Can be used later for ping/pong or messaging
    except WebSocketDisconnect:
        unregister_connection(stream_id, websocket)
        remove_user_from_stream(stream_id, user_id)
        await broadcast_user_list(stream_id)