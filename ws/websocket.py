# ws/websocket.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from db.models import User, Stream, Song
from db.database import get_session
from sqlmodel import Session, select
from utils.memory import add_viber, remove_viber, active_vibers
from routers.queue import queue_map
from typing import Dict, List
import json

websocket_router = APIRouter()
connections: Dict[str, List[WebSocket]] = {}

@websocket_router.websocket("/ws/stream/{stream_id}")
async def stream_ws(websocket: WebSocket, stream_id: str):
    await websocket.accept()

    # Parse initial user ID from query
    params = websocket.query_params
    user_id = params.get("user_id")
    if not user_id:
        await websocket.close()
        return

    # Get user info
    with next(get_session()) as session:
        user = session.exec(select(User).where(User.user_id == user_id)).first()
        if not user:
            await websocket.close()
            return

        # Add to memory
        add_viber(stream_id, {
            "user_id": user.user_id,
            "name": user.name,
            "profile_pic": user.profile_pic
        })

    # Register connection
    if stream_id not in connections:
        connections[stream_id] = []
    connections[stream_id].append(websocket)

    # Send initial sync
    await send_sync(stream_id)

    try:
        while True:
            await websocket.receive_text()  # keep alive (client can ping)
    except WebSocketDisconnect:
        connections[stream_id].remove(websocket)
        remove_viber(stream_id, user_id)
        await send_sync(stream_id)

# 🔄 Sync broadcast
async def send_sync(stream_id: str):
    with next(get_session()) as session:
        stream = session.exec(select(Stream).where(Stream.stream_id == stream_id)).first()
        now_playing = None
        if stream and stream.now_playing_song_id:
            song = session.exec(select(Song).where(Song.song_id == stream.now_playing_song_id)).first()
            if song:
                now_playing = {
                    "song_id": song.song_id,
                    "title": song.title,
                    "artist": song.artist,
                    "duration": song.duration,
                    "thumbnail_url": song.thumbnail_url,
                    "start_time": stream.start_time.isoformat() if stream.start_time else None
                }

    payload = {
        "type": "sync",
        "now_playing": now_playing,
        "queue": queue_map.get(stream_id, []),
        "vibers": active_vibers.get(stream_id, [])
    }

    for ws in connections.get(stream_id, []):
        await ws.send_text(json.dumps(payload))
