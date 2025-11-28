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
from utils.auth import verify_firebase_token
from utils.firebase import get_firestore

router = APIRouter(prefix="/stream", tags=["Stream"])


class CreateStreamRequest(BaseModel):
    title: Optional[str] = None
    visibility: Optional[str] = "public"


class JoinStreamRequest(BaseModel):
    stream_id: str


class LeaveStreamRequest(BaseModel):
    stream_id: str


class PlayNextRequest(BaseModel):
    stream_id: str


def ensure_user(session: Session, user_id: str, name: Optional[str] = None) -> User:
    """
    Ensures a user exists in DB. Creates if not found.
    Also syncs basic profile to Firestore for future chat.
    """
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

    # Sync minimal profile to Firestore
    try:
        db = get_firestore()
        db.collection("users").document(user_id).set(
            {
                "uid": user_id,
                "name": user.name,
                "username": user.username,
                "profile_pic": user.profile_pic,
                "updated_at": datetime.utcnow(),
            },
            merge=True,
        )
    except Exception:
        # Firestore failure should not break core flow
        pass

    return user


@router.post("/create")
def create_stream(
    data: CreateStreamRequest,
    session: Session = Depends(get_session),
    firebase_uid: str = Depends(verify_firebase_token),
):
    user = ensure_user(session, firebase_uid)

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
def join_stream(
    data: JoinStreamRequest,
    session: Session = Depends(get_session),
    firebase_uid: str = Depends(verify_firebase_token),
):
    stream = session.exec(
        select(Stream).where(Stream.stream_id == data.stream_id)
    ).first()

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    user = ensure_user(session, firebase_uid)

    participant = session.exec(
        select(StreamParticipant).where(
            (StreamParticipant.stream_id == data.stream_id)
            & (StreamParticipant.user_id == firebase_uid)
        )
    ).first()

    if not participant:
        participant = StreamParticipant(
            stream_id=data.stream_id,
            user_id=firebase_uid,
            is_admin=False,
        )
        session.add(participant)
        session.commit()

    return {
        "message": f"{user.name} joined stream {data.stream_id}"
    }


@router.post("/leave")
def leave_stream(
    data: LeaveStreamRequest,
    session: Session = Depends(get_session),
    firebase_uid: str = Depends(verify_firebase_token),
):
    stream = session.exec(
        select(Stream).where(Stream.stream_id == data.stream_id)
    ).first()

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    participant = session.exec(
        select(StreamParticipant).where(
            (StreamParticipant.stream_id == data.stream_id)
            & (StreamParticipant.user_id == firebase_uid)
        )
    ).first()

    if not participant:
        raise HTTPException(status_code=404, detail="User not in stream")

    session.delete(participant)
    session.commit()

    _ = session.exec(
        select(func.count()).select_from(StreamParticipant).where(
            StreamParticipant.stream_id == data.stream_id
        )
    ).one()

    return {
        "message": f"User {firebase_uid} left the stream {data.stream_id}"
    }


@router.post("/queue/next")
def play_next(
    data: PlayNextRequest,
    session: Session = Depends(get_session),
    firebase_uid: str = Depends(verify_firebase_token),
):
    stream = session.exec(
        select(Stream).where(Stream.stream_id == data.stream_id)
    ).first()

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    # Mark current as played
    if stream.current_queue_item_id:
        current_item = session.exec(
            select(StreamQueueItem).where(StreamQueueItem.id == stream.current_queue_item_id)
        ).first()

        if current_item:
            current_item.status = "played"
            session.add(current_item)

    # Next queued item
    next_item = session.exec(
        select(StreamQueueItem)
        .where(
            (StreamQueueItem.stream_id == data.stream_id)
            & (StreamQueueItem.status == "queued")
        )
        .order_by(StreamQueueItem.position.asc())
    ).first()

    if not next_item:
        stream.current_queue_item_id = None
        stream.playback_status = "stopped"
        stream.playback_position_ms = 0
        stream.playback_updated_at = datetime.utcnow()

        session.add(stream)
        session.commit()

        notify_stream_background(
            data.stream_id,
            "PLAYER_STATE_UPDATED",
            {"now_playing": None},
        )

        return {"message": "Queue is empty"}

    next_item.status = "playing"
    stream.current_queue_item_id = next_item.id
    stream.playback_status = "playing"
    stream.playback_position_ms = 0
    stream.playback_updated_at = datetime.utcnow()

    session.add(next_item)
    session.add(stream)
    session.commit()

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


@router.get("/participants/{stream_id}")
def get_stream_participants(
    stream_id: str,
    session: Session = Depends(get_session),
    firebase_uid: str = Depends(verify_firebase_token),
):
    """
    Returns full user list in a stream, including admin status.
    """

    participants = session.exec(
        select(StreamParticipant).where(StreamParticipant.stream_id == stream_id)
    ).all()

    if not participants:
        raise HTTPException(status_code=404, detail="Stream not found or has no participants")

    user_ids = [p.user_id for p in participants]

    users = session.exec(
        select(User).where(User.user_id.in_(user_ids))
    ).all()

    result = []
    for p in participants:
        u = next(u for u in users if u.user_id == p.user_id)
        result.append({
            "user_id": u.user_id,
            "name": u.name,
            "username": u.username,
            "profile_pic": u.profile_pic,
            "is_admin": p.is_admin,
            "joined_at": p.joined_at,
            "last_seen_at": p.last_seen_at,
        })

    return {
        "stream_id": stream_id,
        "participants": result,
    }
