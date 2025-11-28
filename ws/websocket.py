# ws/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select
from db.database import get_session
from db.models import User, Stream, Song, StreamQueueItem
from utils.memory import active_vibers, active_connections
from firebase_admin import auth as firebase_auth
import json

router = APIRouter()


def get_user_info(user: User):
    return {
        "user_id": user.user_id,
        "name": user.name,
        "profile_pic": user.profile_pic,
    }


async def broadcast_to_stream(stream_id: str, message: dict):
    """
    Broadcast a JSON message to all active WebSockets in a stream.
    """
    connections = active_connections.get(stream_id, [])
    data = json.dumps(message)
    for ws in list(connections):
        try:
            await ws.send_text(data)
        except Exception:
            connections.remove(ws)


def get_now_playing(session: Session, stream_id: str):
    """
    Read global player state from Stream + metadata from Song.
    """
    stream = session.exec(
        select(Stream).where(Stream.stream_id == stream_id)
    ).first()
    if not stream or not stream.current_queue_item_id:
        return None

    queue_item = session.exec(
        select(StreamQueueItem).where(StreamQueueItem.id == stream.current_queue_item_id)
    ).first()
    if not queue_item:
        return None

    song = session.exec(
        select(Song).where(Song.song_id == queue_item.song_id)
    ).first()
    if not song:
        return None

    return {
        "queue_item_id": queue_item.id,
        "song_id": song.song_id,
        "title": song.title,
        "artist": song.artist,
        "thumbnail_url": song.thumbnail_url,
        "audio_url": song.audio_url,
        "status": stream.playback_status,
        "position_ms": stream.playback_position_ms,
        "updated_at": stream.playback_updated_at.isoformat()
        if stream.playback_updated_at
        else None,
    }


def get_queue_for_stream(session: Session, stream_id: str):
    """
    Ordered queue (only queued/playing items) with metadata from Song.
    """
    items = session.exec(
        select(StreamQueueItem)
        .where(
            (StreamQueueItem.stream_id == stream_id)
            & (StreamQueueItem.status.in_(["queued", "playing"]))
        )
        .order_by(StreamQueueItem.position.asc())
    ).all()

    song_ids = [i.song_id for i in items]
    if not song_ids:
        return []

    songs = session.exec(
        select(Song).where(Song.song_id.in_(song_ids))
    ).all()
    song_map = {s.song_id: s for s in songs}

    queue = []
    for item in items:
        song = song_map.get(item.song_id)
        if not song:
            continue
        queue.append(
            {
                "queue_item_id": item.id,
                "song_id": song.song_id,
                "title": song.title,
                "artist": song.artist,
                "thumbnail_url": song.thumbnail_url,
                "audio_url": song.audio_url,
                "position": item.position,
                "status": item.status,
                "added_by": item.added_by,
                "added_at": item.added_at.isoformat(),
            }
        )
    return queue


@router.websocket("/ws/stream/{stream_id}")
async def stream_ws(websocket: WebSocket, stream_id: str):
    """
    WebSocket connection per stream.

    Auth options:
    - Preferred: ?token=<FIREBASE_ID_TOKEN>
    - Dev fallback: ?user_id=<uid>
    """
    await websocket.accept()

    params = websocket.query_params
    token = params.get("token")
    user_id = params.get("user_id")

    if token:
        try:
            decoded = firebase_auth.verify_id_token(token)
            user_id = decoded["uid"]
        except Exception:
            await websocket.send_text(json.dumps({"type": "ERROR", "message": "Invalid Firebase token"}))
            await websocket.close()
            return

    if not user_id:
        await websocket.send_text(json.dumps({"type": "ERROR", "message": "Missing user_id/token"}))
        await websocket.close()
        return

    session = next(get_session())

    # Get user from DB
    user = session.exec(
        select(User).where(User.user_id == user_id)
    ).first()
    if not user:
        await websocket.send_text(json.dumps({"type": "ERROR", "message": "User not found"}))
        await websocket.close()
        return

    # Get stream from DB
    stream = session.exec(
        select(Stream).where(Stream.stream_id == stream_id)
    ).first()
    if not stream:
        await websocket.send_text(json.dumps({"type": "ERROR", "message": "Stream not found"}))
        await websocket.close()
        return

    active_connections.setdefault(stream_id, []).append(websocket)
    vibers = active_vibers.setdefault(stream_id, [])

    if not any(v["user_id"] == user.user_id for v in vibers):
        vibers.append(get_user_info(user))

    await broadcast_to_stream(
        stream_id,
        {
            "type": "STREAM_STATE",
            "vibers": vibers,
            "now_playing": get_now_playing(session, stream_id),
            "queue": get_queue_for_stream(session, stream_id),
        },
    )

    try:
        while True:
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        conns = active_connections.get(stream_id, [])
        if websocket in conns:
            conns.remove(websocket)
        vibers = active_vibers.get(stream_id, [])
        active_vibers[stream_id] = [
            v for v in vibers if v["user_id"] != user.user_id
        ]
        if not active_vibers[stream_id]:
            active_vibers.pop(stream_id, None)

        await broadcast_to_stream(
            stream_id,
            {
                "type": "VIBERS_UPDATED",
                "vibers": active_vibers.get(stream_id, []),
                "now_playing": get_now_playing(session, stream_id),
                "queue": get_queue_for_stream(session, stream_id),
            },
        )
