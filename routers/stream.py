from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from db.database import get_session
from db.models import Stream, User
from pydantic import BaseModel
from typing import List, Optional
import uuid

router = APIRouter()

# ===============================
# Models
# ===============================
class CreateStreamRequest(BaseModel):
    user_id: str  # Admin's ID

class JoinStreamRequest(BaseModel):
    user_id: str
    stream_id: str

class RemoveUserRequest(BaseModel):
    admin_id: str
    user_id: str
    stream_id: str

# ===============================
# Create Stream
# ===============================
@router.post("/create")
def create_stream(data: CreateStreamRequest, session: Session = Depends(get_session)):
    """Creates a new stream and assigns the creator as admin."""
    user = session.exec(select(User).where(User.user_id == data.user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Create unique stream ID
    stream_id = str(uuid.uuid4())[:8]
    stream = Stream(stream_id=stream_id, admin_id=data.user_id)
    session.add(stream)

    # Update user’s current stream
    user.current_stream_id = stream_id
    session.commit()

    return {
        "message": "Stream created successfully",
        "stream_id": stream_id,
        "admin_id": data.user_id
    }

# ===============================
# Join Stream
# ===============================
@router.post("/join")
def join_stream(data: JoinStreamRequest, session: Session = Depends(get_session)):
    """Allows a user to join an existing stream."""
    stream = session.exec(select(Stream).where(Stream.stream_id == data.stream_id)).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    user = session.exec(select(User).where(User.user_id == data.user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.current_stream_id = data.stream_id
    session.commit()

    return {
        "message": f"User {user.name} joined stream {data.stream_id}",
        "stream_id": data.stream_id
    }

# ===============================
# Get Users in a Stream
# ===============================
@router.get("/users/{stream_id}")
def get_users_in_stream(stream_id: str, session: Session = Depends(get_session)):
    """Fetch all users currently in a stream."""
    users = session.exec(select(User).where(User.current_stream_id == stream_id)).all()
    return {"stream_id": stream_id, "users": users}

# ===============================
# Remove User (Admin Only)
# ===============================
@router.post("/remove_user")
def remove_user(data: RemoveUserRequest, session: Session = Depends(get_session)):
    """Allows admin to remove a user from their stream."""
    stream = session.exec(select(Stream).where(Stream.stream_id == data.stream_id)).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    if stream.admin_id != data.admin_id:
        raise HTTPException(status_code=403, detail="Only the admin can remove users")

    user = session.exec(select(User).where(User.user_id == data.user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.current_stream_id = None
    session.commit()

    return {"message": f"User {data.user_id} removed from stream {data.stream_id}"}
