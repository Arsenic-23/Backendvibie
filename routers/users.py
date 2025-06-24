from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from db.database import get_session
from db.models import User, Stream
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# ✅ Updated to match frontend payload exactly
class JoinRequest(BaseModel):
    telegram_id: str
    name: str
    username: str | None = None       # ← added to fix 422
    profile_pic: str | None = None
    stream_id: str | None = None      # Optional; fallback to telegram_id

@router.post("/join")
def join_user(data: JoinRequest, session: Session = Depends(get_session)):
    # ✅ Fallback: if no stream_id provided, use user's own Telegram ID
    stream_id = data.stream_id or data.telegram_id

    # ✅ Create stream if it doesn't exist
    stream = session.exec(select(Stream).where(Stream.stream_id == stream_id)).first()
    if not stream:
        stream = Stream(stream_id=stream_id)
        session.add(stream)
        session.commit()
        session.refresh(stream)

    # ✅ Create or update user record
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