from fastapi import WebSocket
from database import connections, add_user_to_stream, remove_user_from_stream
from models.stream import UserProfile
from typing import List

async def stream_websocket_endpoint(websocket: WebSocket, stream_id: str, user_id: int, username: str):
    # Connect the WebSocket
    await websocket.accept()
    # Create user profile object
    user_profile = UserProfile(user_id=user_id, username=username)

    # Add user to the stream (in-memory store)
    add_user_to_stream(stream_id, user_profile.dict())
    connections[stream_id].append(websocket)

    # Notify all users in the stream about the new user joining
    await notify_stream(stream_id)

    try:
        while True:
            # Keep the WebSocket connection alive
            data = await websocket.receive_text()
            # You can handle additional WebSocket events here (e.g., chat messages)
    except Exception as e:
        # Handle any WebSocket disconnections
        pass
    finally:
        # Remove user from stream on WebSocket disconnect
        remove_user_from_stream(stream_id, user_id)
        connections[stream_id].remove(websocket)

        # Notify remaining users about the user leaving
        await notify_stream(stream_id)

async def notify_stream(stream_id: str):
    # Retrieve all users in the stream
    users = [user['username'] for user in streams[stream_id]]
    # Broadcast the list of users to all connected WebSockets
    for connection in connections[stream_id]:
        await connection.send_json({"users": users})