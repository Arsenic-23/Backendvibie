from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from db.database import get_session
from db.models import User, Stream
from pydantic import BaseModel
from typing import Union
import uuid

router = APIRouter()

class JoinRequest(BaseModel):
    telegram_id: Union[str, int]
    name: str
    username: str | None = None
    profile_pic: str | None = None
    stream_id: Union[str, int] | None = None

@router.post("/join")
def join_user(data: JoinRequest, session: Session = Depends(get_session)):
    """Create or join user to a stream. Creates a new stream if none provided."""
    telegram_id = str(data.telegram_id)
    stream_id = str(data.stream_id) if data.stream_id else str(uuid.uuid4())[:8]

    # Fetch or create stream
    stream = session.exec(select(Stream).where(Stream.stream_id == stream_id)).first()
    if not stream:
        stream = Stream(stream_id=stream_id, admin_id=telegram_id)
        session.add(stream)
        session.commit()

    # Fetch or create user
    user = session.exec(select(User).where(User.user_id == telegram_id)).first()
    if user:
        user.name = data.name
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

    session.commit()

    return {
        "message": "User joined stream successfully.",
        "user": {
            "user_id": telegram_id,
            "name": data.name,
            "profile_pic": data.profile_pic
        },
        "stream_id": stream_id
    }
