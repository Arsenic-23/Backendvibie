# routers/stream.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from db.database import get_session
from db.models import Stream, User, StreamParticipant, StreamQueueItem, Song
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime
from utils.notify import notify_stream_background

router = APIRouter(prefix="/stream", tags=["Stream"])


class CreateStreamRequest(BaseModel):
    user_id: str      # Firebase uid
    title: Optional[str] = None
    visibility: Optional[str] = "public"


class JoinStreamRequest(BaseModel):
    user_id: str
    stream_id: str


class LeaveStreamRequest(BaseModel):
    user_id: str
    stream_id: str


class PlayNextRequest(BaseModel):
    stream_id: str
    user_id: str  # who is triggering (for permissions later)


def ensure_user(session: Session, user_id: str, name: Optional[str] = None) -> User:
    user = session.exec(
        select(User).where(User.user_id == user_id)
    ).first()
    if not user:
        user = User(
            user_id=user_id,
            name=name or f"User {user_id}",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


@router.post("/create")
def create_stream(data: CreateStreamRequest, session: Session = Depends(get_session)):
    user = ensure_user(session, data.user_id)

    # Short stream id as code
    stream_id = str(uuid.uuid4())[:8]

    new_stream = Stream(
        stream_id=stream_id,
        host_id=user.user_id,
        visibility=data.visibility or "public",
        title=data.title or f"{user.name}'s Stream",
        playback_status="stopped",
        playback_position_ms=0,
        playback_updated_at=None,
        start_time=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    session.add(new_stream)

    participant = StreamParticipant(
        stream_id=stream_id,
        user_id=user.user_id,
        is_admin=True,
    )
    session.add(participant)

    session.commit()
    session.refresh(new_stream)

    return {
        "message": "Stream created successfully",
        "stream_id": new_stream.stream_id,
        "title": new_stream.title,
        "visibility": new_stream.visibility,
    }


@router.post("/join")
def join_stream(data: JoinStreamRequest, session: Session = Depends(get_session)):
    stream = session.exec(
        select(Stream).where(Stream.stream_id == data.stream_id)
    ).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    user = ensure_user(session, data.user_id)

    participant = session.exec(
        select(StreamParticipant).where(
            (StreamParticipant.stream_id == data.stream_id)
            & (StreamParticipant.user_id == data.user_id)
        )
    ).first()

    if not participant:
        participant = StreamParticipant(
            stream_id=data.stream_id,
            user_id=data.user_id,
            is_admin=False,
        )
        session.add(participant)
        session.commit()

    return {
        "message": f"{user.name} joined stream {data.stream_id}",
    }


@router.post("/leave")
def leave_stream(data: LeaveStreamRequest, session: Session = Depends(get_session)):
    stream = session.exec(
        select(Stream).where(Stream.stream_id == data.stream_id)
    ).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    participant = session.exec(
        select(StreamParticipant).where(
            (StreamParticipant.stream_id == data.stream_id)
            & (StreamParticipant.user_id == data.user_id)
        )
    ).first()

    if not participant:
        raise HTTPException(status_code=404, detail="User not in stream")

    session.delete(participant)
    session.commit()

    # If no participants left, you can either delete the stream or leave it
    remaining = session.exec(
        select(func.count()).select_from(StreamParticipant).where(
            StreamParticipant.stream_id == data.stream_id
        )
    ).one()

    if remaining[0] == 0:
        # For now, just keep the stream; you can choose to delete or mark inactive.
        pass

    return {
        "message": f"User {data.user_id} left the stream {data.stream_id}",
    }


@router.post("/queue/next")
def play_next(data: PlayNextRequest, session: Session = Depends(get_session)):
    """
    Advance to next track in queue and update global player state.
    """
    stream = session.exec(
        select(Stream).where(Stream.stream_id == data.stream_id)
    ).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    # Mark current as played
    if stream.current_queue_item_id:
        current_item = session.exec(
            select(StreamQueueItem).where(
                StreamQueueItem.id == stream.current_queue_item_id
            )
        ).first()
        if current_item:
            current_item.status = "played"
            session.add(current_item)

    # Find next queued item
    next_item = session.exec(
        select(StreamQueueItem)
        .where(
            (StreamQueueItem.stream_id == data.stream_id)
            & (StreamQueueItem.status == "queued")
        )
        .order_by(StreamQueueItem.position.asc())
    ).first()

    if not next_item:
        # No more songs
        stream.current_queue_item_id = None
        stream.playback_status = "stopped"
        stream.playback_position_ms = 0
        stream.playback_updated_at = datetime.utcnow()
        session.add(stream)
        session.commit()

        notify_stream_background(
            data.stream_id,
            "PLAYER_STATE_UPDATED",
            {
                "now_playing": None,
            },
        )
        return {"message": "Queue is empty"}

    # Set next as playing
    next_item.status = "playing"
    stream.current_queue_item_id = next_item.id
    stream.playback_status = "playing"
    stream.playback_position_ms = 0
    stream.playback_updated_at = datetime.utcnow()

    session.add(next_item)
    session.add(stream)
    session.commit()

    # Build payload
    song = session.exec(
        select(Song).where(Song.song_id == next_item.song_id)
    ).first()

    now_playing = {
        "queue_item_id": next_item.id,
        "song_id": song.song_id if song else next_item.song_id,
        "title": song.title if song else None,
        "artist": song.artist if song else None,
        "thumbnail_url": song.thumbnail_url if song else None,
        "audio_url": song.audio_url if song else None,
        "status": stream.playback_status,
        "position_ms": stream.playback_position_ms,
        "updated_at": stream.playback_updated_at.isoformat(),
    }

    notify_stream_background(
        data.stream_id,
        "PLAYER_STATE_UPDATED",
        {"now_playing": now_playing},
    )

    return {
        "message": f"Now playing: {now_playing['title']}",
        "now_playing": now_playing,
    }