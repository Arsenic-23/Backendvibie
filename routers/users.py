# routers/users.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from db.database import get_session
from db.models import User, Stream
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class JoinRequest(BaseModel):
    telegram_id: str
    name: str
    profile_pic: str | None = None
    stream_id: str | None = None  # Optional; fallback to telegram_id

@router.post("/join")
def join_user(data: JoinRequest, session: Session = Depends(get_session)):
    # fallback: if no stream_id provided, use user's ID to create personal stream
    stream_id = data.stream_id or data.telegram_id

    # 1. Create stream if it doesn't exist
    stream = session.exec(select(Stream).where(Stream.stream_id == stream_id)).first()
    if not stream:
        stream = Stream(stream_id=stream_id)
        session.add(stream)
        session.commit()
        session.refresh(stream)

    # 2. Create or update user
    user = session.exec(select(User).where(User.user_id == data.telegram_id)).first()
    if user:
        user.name = data.name
        user.profile_pic = data.profile_pic
        user.current_stream_id = stream_id
    else:
        user = User(
            user_id=data.telegram_id,
            name=data.name,
            profile_pic=data.profile_pic,
            current_stream_id=stream_id
        )
        session.add(user)

    session.commit()
    session.refresh(user)

    return {
        "message": "User joined stream successfully.",
        "user": {
            "user_id": user.user_id,
            "name": user.name,
            "profile_pic": user.profile_pic
        },
        "stream_id": stream_id
    }
