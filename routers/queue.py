# routers/queue.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from db.database import get_session
from db.models import Song, Stream, StreamQueueItem, User
from typing import Optional
from pydantic import BaseModel
from utils.notify import notify_stream_background
from utils.auth import verify_firebase_token

router = APIRouter(prefix="/queue", tags=["Queue"])


class AddSongRequest(BaseModel):
    stream_id: str
    song_id: str           
    title: str
    artist: Optional[str] = None
    duration: Optional[int] = None
    thumbnail_url: Optional[str] = None
    audio_url: Optional[str] = None


def ensure_user(session: Session, user_id: str) -> User:
    user = session.exec(
        select(User).where(User.user_id == user_id)
    ).first()
    if not user:
        user = User(user_id=user_id, name=f"User {user_id}")
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


@router.post("/add")
def add_song_to_queue(
    data: AddSongRequest,
    session: Session = Depends(get_session),
    firebase_uid: str = Depends(verify_firebase_token),
)

    ensure_user(session, firebase_uid)

    stream = session.exec(
        select(Stream).where(Stream.stream_id == data.stream_id)
    ).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    song = session.exec(
        select(Song).where(Song.song_id == data.song_id)
    ).first()
    if not song:
        song = Song(
            song_id=data.song_id,
            title=data.title,
            artist=data.artist,
            duration=data.duration,
            thumbnail_url=data.thumbnail_url,
            audio_url=data.audio_url,
        )
        session.add(song)
        session.commit()
        session.refresh(song)
        
    max_pos = session.exec(
        select(func.max(StreamQueueItem.position)).where(
            StreamQueueItem.stream_id == data.stream_id
        )
    ).first()
    next_pos = (max_pos or 0) + 1

    queue_item = StreamQueueItem(
        stream_id=data.stream_id,
        song_id=song.song_id,
        position=next_pos,
        status="queued",
        added_by=firebase_uid,
    )
    session.add(queue_item)
    session.commit()
    session.refresh(queue_item)

    from ws.websocket import get_queue_for_stream
    queue = get_queue_for_stream(session, data.stream_id)
    notify_stream_background(
        data.stream_id,
        "QUEUE_UPDATED",
        {"queue": queue},
    )

    return {"message": "Song added to queue", "queue_item_id": queue_item.id, "queue": queue}


@router.get("/{stream_id}")
def get_queue(
    stream_id: str,
    session: Session = Depends(get_session),
    firebase_uid: str = Depends(verify_firebase_token),
):
    from ws.websocket import get_queue_for_stream
    queue = get_queue_for_stream(session, stream_id)
    return {"queue": queue}


@router.delete("/{stream_id}/pop")
def pop_song(
    stream_id: str,
    session: Session = Depends(get_session),
    firebase_uid: str = Depends(verify_firebase_token),
):
    """
    Remove the first queued item (lowest position) and return it.
    """
    item = session.exec(
        select(StreamQueueItem)
        .where(
            (StreamQueueItem.stream_id == stream_id)
            & (StreamQueueItem.status == "queued")
        )
        .order_by(StreamQueueItem.position.asc())
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Queue empty")

    item.status = "removed"
    session.add(item)
    session.commit()

    from ws.websocket import get_queue_for_stream
    queue = get_queue_for_stream(session, stream_id)
    notify_stream_background(
        stream_id,
        "QUEUE_UPDATED",
        {"queue": queue},
    )

    return {"message": "Song removed from queue", "removed_queue_item_id": item.id}
