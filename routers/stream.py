# routers/stream.py

from fastapi import APIRouter, HTTPException
from database import add_user_to_stream, get_users_in_stream
from schemas.stream import CreateStreamRequest, CreateStreamResponse, JoinStreamRequest, UserProfile
from utils import generate_stream_id, generate_deep_link

router = APIRouter()

@router.post("/create", response_model=CreateStreamResponse)
def create_stream(data: CreateStreamRequest):
    stream_id = generate_stream_id(data.stream_type, data.owner_id)
    deep_link = generate_deep_link(stream_id)
    return {"stream_id": stream_id, "deep_link": deep_link}

@router.post("/join")
def join_stream(data: JoinStreamRequest):
    if not data.stream_id:
        raise HTTPException(status_code=400, detail="Stream ID required")
    add_user_to_stream(data.stream_id, data.user.dict())
    return {"message": f"{data.user.username} joined stream {data.stream_id}"}

@router.get("/vibers/{stream_id}", response_model=list[UserProfile])
def get_stream_users(stream_id: str):
    return get_users_in_stream(stream_id)