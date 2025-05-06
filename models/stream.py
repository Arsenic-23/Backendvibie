from pydantic import BaseModel

class UserProfile(BaseModel):
    user_id: int
    username: str
    profile_pic: str = ""

class CreateStreamRequest(BaseModel):
    stream_type: str  # "group" or "personal"
    owner_id: int

class CreateStreamResponse(BaseModel):
    stream_id: str
    deep_link: str

class JoinStreamRequest(BaseModel):
    stream_id: str
    user: UserProfile