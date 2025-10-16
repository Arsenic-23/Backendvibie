from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from db.database import get_session
from db.models import User, Stream
from pydantic import BaseModel
from typing import Union
import uuid

router = APIRouter(prefix="/user", tags=["User"])

class JoinRequest(BaseModel):
    telegram_id: Union[str, int]
    name: str
    username: str | None = None
    profile_pic: str | None = None
    stream_id: Union[str, int] | None = None

@router.post("/join")
def join_user(data: JoinRequest, session: Session = Depends(get_session)):
    telegram_id = str(data.telegram_id)
    stream_id = str(data.stream_id) if data.stream_id else str(uuid.uuid4())[:8]

    # Fetch or create stream
    stream = session.exec(select(Stream).where(Stream.stream_id == stream_id)).first()
    if not stream:
        stream = Stream(
            stream_id=stream_id,
            admins=[telegram_id],
            participants=[telegram_id],
            blocked=[],
            queue=[],
            now_playing_song_id=None,
            visibility="public",
            title=f"{data.name}'s Stream"
        )
        session.add(stream)

    # Fetch or create user
    user = session.exec(select(User).where(User.user_id == telegram_id)).first()
    if user:
        user.name = data.name
        user.username = data.username
        user.profile_pic = data.profile_pic
        user.current_stream_id = stream_id
    else:
        user = User(
            user_id=telegram_id,
            name=data.name,
            username=data.username,
            profile_pic=data.profile_pic,
            current_stream_id=stream_id
        )
        session.add(user)

    if telegram_id not in stream.participants:
        stream.participants.append(telegram_id)

    session.commit()
    session.refresh(user)
    session.refresh(stream)

    return {
        "message": "User joined stream successfully",
        "user": {
            "user_id": telegram_id,
            "name": data.name,
            "username": data.username,
            "profile_pic": data.profile_pic
        },
        "stream_id": stream_id
    }
