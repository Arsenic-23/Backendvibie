# routers/stream.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from db.database import get_session
from db.models import Stream, User, Song
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime

router = APIRouter(prefix="/stream", tags=["Stream"])

# ----------------------------
# Request Models
# ----------------------------
class CreateStreamRequest(BaseModel):
    user_id: str
    title: Optional[str] = None
    visibility: Optional[str] = "public"

class JoinStreamRequest(BaseModel):
    user_id: str
    stream_id: str

class LeaveStreamRequest(BaseModel):
    user_id: str
    stream_id: str

class RemoveUserRequest(BaseModel):
    admin_id: str
    user_id: str
    stream_id: str

class AddSongRequest(BaseModel):
    stream_id: str
    song_id: str

class PlayNextRequest(BaseModel):
    stream_id: str

# ----------------------------
# Create Stream
# ----------------------------
@router.post("/create")
def create_stream(data: CreateStreamRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.user_id == data.user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stream_id = str(uuid.uuid4())[:8]
    new_stream = Stream(
        stream_id=stream_id,
        admins=[data.user_id],
        participants=[data.user_id],
        blocked=[],
        queue=[],
        now_playing_song_id=None,
        visibility=data.visibility,
        title=data.title or f"{user.name}'s Stream",
        start_time=datetime.utcnow(),
        created_at=datetime.utcnow()
    )
    session.add(new_stream)
    user.current_stream_id = stream_id
    session.commit()
    session.refresh(new_stream)

    return {
        "message": "Stream created successfully",
        "stream_id": new_stream.stream_id,
        "title": new_stream.title,
        "visibility": new_stream.visibility
    }

# ----------------------------
# Join Stream
# ----------------------------
@router.post("/join")
def join_stream(data: JoinStreamRequest, session: Session = Depends(get_session)):
    stream = session.exec(select(Stream).where(Stream.stream_id == data.stream_id)).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    user = session.exec(select(User).where(User.user_id == data.user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.user_id in stream.blocked:
        raise HTTPException(status_code=403, detail="You are blocked from this stream")

    if data.user_id not in stream.participants:
        stream.participants.append(data.user_id)

    user.current_stream_id = stream.stream_id
    session.commit()
    session.refresh(stream)

    return {"message": f"{user.name} joined stream {data.stream_id}", "participants": stream.participants}

# ----------------------------
# Leave Stream
# ----------------------------
@router.post("/leave")
def leave_stream(data: LeaveStreamRequest, session: Session = Depends(get_session)):
    stream = session.exec(select(Stream).where(Stream.stream_id == data.stream_id)).first()
    user = session.exec(select(User).where(User.user_id == data.user_id)).first()

    if not stream or not user:
        raise HTTPException(status_code=404, detail="Stream or User not found")

    if data.user_id in stream.participants:
        stream.participants.remove(data.user_id)
    if data.user_id in stream.admins:
        stream.admins.remove(data.user_id)

    user.current_stream_id = None

    if not stream.participants:
        session.delete(stream)

    session.commit()
    return {"message": f"{user.name} left the stream {data.stream_id}"}

# ----------------------------
# Remove User (Admin Only)
# ----------------------------
@router.post("/remove_user")
def remove_user(data: RemoveUserRequest, session: Session = Depends(get_session)):
    stream = session.exec(select(Stream).where(Stream.stream_id == data.stream_id)).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    if data.admin_id not in stream.admins:
        raise HTTPException(status_code=403, detail="Only admins can remove users")

    user = session.exec(select(User).where(User.user_id == data.user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.user_id in stream.participants:
        stream.participants.remove(data.user_id)
    user.current_stream_id = None
    session.commit()
    return {"message": f"User {user.name} removed from stream {data.stream_id}"}

# ----------------------------
# Add Song
# ----------------------------
@router.post("/queue/add")
def add_song_to_queue(data: AddSongRequest, session: Session = Depends(get_session)):
    stream = session.exec(select(Stream).where(Stream.stream_id == data.stream_id)).first()
    song = session.exec(select(Song).where(Song.song_id == data.song_id)).first()
    if not stream or not song:
        raise HTTPException(status_code=404, detail="Stream or Song not found")
    stream.queue.append(song.song_id)
    session.commit()
    return {"message": f"Song '{song.title}' added", "queue": stream.queue}

# ----------------------------
# Play Next Song
# ----------------------------
@router.post("/queue/next")
def play_next(data: PlayNextRequest, session: Session = Depends(get_session)):
    stream = session.exec(select(Stream).where(Stream.stream_id == data.stream_id)).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    if not stream.queue:
        stream.now_playing_song_id = None
        session.commit()
        return {"message": "Queue is empty"}

    next_song_id = stream.queue.pop(0)
    stream.now_playing_song_id = next_song_id
    session.commit()
    song = session.exec(select(Song).where(Song.song_id == next_song_id)).first()
    return {"message": f"Now playing: {song.title}", "queue": stream.queue}
