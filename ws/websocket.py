from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select
from db.database import get_session
from db.models import User, Stream, Song
from utils.memory import active_vibers, active_connections
import json

router = APIRouter()

def get_user_info(user: User):
    return {
        "user_id": user.user_id,
        "name": user.name,
        "profile_pic": user.profile_pic
    }

async def broadcast_to_stream(stream_id: str, message: dict):
    for ws in active_connections.get(stream_id, []):
        await ws.send_text(json.dumps(message))

@router.websocket("/ws/stream/{stream_id}")
async def stream_ws(websocket: WebSocket, stream_id: str, user_id: str):
    await websocket.accept()

    session = next(get_session())
    
    # Get user from DB
    user = session.exec(select(User).where(User.user_id == user_id)).first()
    if not user:
        await websocket.send_text(json.dumps({"error": "User not found"}))
        await websocket.close()
        return

    # Add user to active vibers and connections
    active_vibers.setdefault(stream_id, []).append(get_user_info(user))
    active_connections.setdefault(stream_id, []).append(websocket)

    # Send updated stream state to everyone
    await broadcast_to_stream(stream_id, {
        "type": "sync",
        "vibers": active_vibers[stream_id],
        "now_playing": get_now_playing(session, stream_id),
        "queue": get_queue_for_stream(session, stream_id)
    })

    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        # Remove user from memory
        active_vibers[stream_id] = [v for v in active_vibers[stream_id] if v["user_id"] != user_id]
        active_connections[stream_id].remove(websocket)

        # Update remaining users
        await broadcast_to_stream(stream_id, {
            "type": "sync",
            "vibers": active_vibers[stream_id],
            "now_playing": get_now_playing(session, stream_id),
            "queue": get_queue_for_stream(session, stream_id)
        })

# Utility to get now playing song details
def get_now_playing(session: Session, stream_id: str):
    stream = session.exec(select(Stream).where(Stream.stream_id == stream_id)).first()
    if not stream or not stream.now_playing_song_id:
        return None

    song = session.exec(select(Song).where(Song.id == stream.now_playing_song_id)).first()
    return {
        "id": song.id,
        "title": song.title,
        "artist": song.artist,
        "thumbnail": song.thumbnail,
        "url": song.url
    } if song else None

# Utility to get queue for stream
def get_queue_for_stream(session: Session, stream_id: str):
    return [
        {
            "id": song.id,
            "title": song.title,
            "artist": song.artist,
            "thumbnail": song.thumbnail,
            "url": song.url
        }
        for song in session.exec(select(Song).where(Song.stream_id == stream_id)).all()
    ]