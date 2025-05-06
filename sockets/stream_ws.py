from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI()

# In-memory streams data (for example, in production, you would use a database)
streams = {}
active_connections = {}

class User(BaseModel):
    user_id: int
    username: str
    profile_pic: str

@app.post("/join")
async def join_stream(stream_id: str, user: User, websocket: WebSocket):
    # Add user to the stream if not already in the stream
    if stream_id not in streams:
        streams[stream_id] = []
    if any(u['user_id'] == user.user_id for u in streams[stream_id]):
        raise HTTPException(status_code=400, detail="User already in stream")
    
    # Add user to stream
    streams[stream_id].append(user.dict())

    # If this is the first user in the stream, create a list of active connections for this stream
    if stream_id not in active_connections:
        active_connections[stream_id] = []

    # Add this websocket connection to the stream
    active_connections[stream_id].append(websocket)

    # Notify all users that a new user joined the stream
    await notify_stream(stream_id)

    return {"message": "User added to stream", "stream_id": stream_id, "user": user}

@app.post("/exit")
async def exit_stream(stream_id: str, user: User, websocket: WebSocket):
    # Check if the stream exists
    if stream_id not in streams:
        raise HTTPException(status_code=404, detail="Stream not found")

    # Remove user from the stream
    stream = streams[stream_id]
    user_index = next((index for (index, u) in enumerate(stream) if u['user_id'] == user.user_id), None)

    if user_index is None:
        raise HTTPException(status_code=404, detail="User not found in the stream")

    # Remove the user
    streams[stream_id].pop(user_index)

    # Remove WebSocket connection from active connections
    if websocket in active_connections[stream_id]:
        active_connections[stream_id].remove(websocket)

    # Notify all users that a user left the stream
    await notify_stream(stream_id)

    return {"message": "User removed from stream", "stream_id": stream_id, "user": user}

@app.get("/stream/{stream_id}")
async def get_stream(stream_id: str):
    # Check if the stream exists
    if stream_id not in streams:
        raise HTTPException(status_code=404, detail="Stream not found")

    return {"stream_id": stream_id, "participants": streams[stream_id]}

async def notify_stream(stream_id: str):
    # Notify all connected users in the stream about the updated participants list
    participants = streams.get(stream_id, [])
    message = {"stream_id": stream_id, "participants": participants}

    # Broadcast message to all connected users in this stream
    if stream_id in active_connections:
        for websocket in active_connections[stream_id]:
            await websocket.send_json(message)

@app.websocket("/ws/{stream_id}")
async def websocket_endpoint(websocket: WebSocket, stream_id: str):
    # Accept WebSocket connection
    await websocket.accept()

    # Add the WebSocket connection to the active connections list for the stream
    if stream_id not in active_connections:
        active_connections[stream_id] = []

    active_connections[stream_id].append(websocket)

    try:
        while True:
            # Keep the WebSocket connection open
            data = await websocket.receive_text()  # Just to keep the connection alive
            # You can send updates to the WebSocket here, e.g., on specific messages
    except WebSocketDisconnect:
        # Handle WebSocket disconnection (remove the user from active connections)
        active_connections[stream_id].remove(websocket)
        # Notify others when a user leaves
        await notify_stream(stream_id)