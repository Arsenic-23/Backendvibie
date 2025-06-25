from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from db.database import get_session
from db.models import User, Stream
from pydantic import BaseModel
from typing import Union

router = APIRouter()

class JoinRequest(BaseModel):
    telegram_id: Union[str, int]
    name: str
    username: str | None = None
    profile_pic: str | None = None
    stream_id: Union[str, int] | None = None

@router.post("/join")
def join_user(data: JoinRequest, session: Session = Depends(get_session)):
    try:
        telegram_id = str(data.telegram_id)
        stream_id = str(data.stream_id or data.telegram_id)

        # Create or fetch stream
        stream = session.exec(select(Stream).where(Stream.stream_id == stream_id)).first()
        if not stream:
            stream = Stream(stream_id=stream_id)
            session.add(stream)
            session.commit()

        # Create or update user
        user = session.exec(select(User).where(User.user_id == telegram_id)).first()
        if user:
            user.name = data.name
            user.profile_pic = data.profile_pic
            user.current_stream_id = stream_id
        else:
            user = User(
                user_id=telegram_id,
                name=data.name,
                profile_pic=data.profile_pic,
                current_stream_id=stream_id
            )
            session.add(user)

        session.commit()

        # ✅ Manually construct safe response (no session.refresh)
        return {
            "message": "User joined stream successfully.",
            "user": {
                "user_id": telegram_id,
                "name": data.name,
                "profile_pic": data.profile_pic
            },
            "stream_id": stream_id
        }

    except Exception as e:
        print(f"[JOIN ERROR]: {e}")
        raise HTTPException(status_code=500, detail="Join failed")