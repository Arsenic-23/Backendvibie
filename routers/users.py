from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from db.database import get_session
from db.models import User, Stream
from pydantic import BaseModel
from typing import Union
import uuid
from datetime import datetime

router = APIRouter(prefix="/user", tags=["User"])

class JoinRequest(BaseModel):
    telegram_id: Union[str, int]
    name: str
    username: str | None = None
    profile_pic: str | None = None
    stream_id: Union[str, int] | None = None
    visibility: str | None = "public"  # Optional visibility for auto-created streams
    title: str | None = None  # Optional custom title for auto-created streams

@router.post("/join")
def join_user(data: JoinRequest, session: Session = Depends(get_session)):
    telegram_id = str(data.telegram_id)
    stream_id = str(data.stream_id) if data.stream_id else str(uuid.uuid4())[:8]

    # ----------------------------
    # Fetch or create user
    # ----------------------------
    user = session.exec(select(User).where(User.user_id == telegram_id)).first()
    if not user:
        user = User(
            user_id=telegram_id,
            name=data.name,
            username=data.username,
            profile_pic=data.profile_pic,
            current_stream_id=None
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    else:
        # Update user info in case it changed
        user.name = data.name
        user.username = data.username
        user.profile_pic = data.profile_pic

    # ----------------------------
    # Fetch or create stream
    # ----------------------------
    stream = session.exec(select(Stream).where(Stream.stream_id == stream_id)).first()
    if not stream:
        stream = Stream(
            stream_id=stream_id,
            admins=[telegram_id],
            participants=[telegram_id],
            blocked=[],
            queue=[],
            now_playing_song_id=None,
            visibility=data.visibility or "public",
            title=data.title or f"{data.name}'s Stream",
            start_time=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        session.add(stream)
    else:
        # Add user to participants if not already
        if telegram_id not in stream.participants:
            stream.participants.append(telegram_id)
        # Make sure user is admin if they created the stream
        if telegram_id not in stream.admins:
            stream.admins.append(telegram_id)

    # ----------------------------
    # Update user's current stream
    # ----------------------------
    user.current_stream_id = stream_id

    session.commit()
    session.refresh(user)
    session.refresh(stream)

    return {
        "message": "User joined stream successfully",
        "user": {
            "user_id": telegram_id,
            "name": user.name,
            "username": user.username,
            "profile_pic": user.profile_pic
        },
        "stream_id": stream_id
    }
