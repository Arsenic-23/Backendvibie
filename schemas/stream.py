from pydantic import BaseModel

class TelegramUser(BaseModel):
    user_id: int
    first_name: str
    username: str
    photo_url: str = ""

class UserProfile(BaseModel):
    user_id: int
    name: str
    profile_pic: str = ""

class CreateStreamRequest(BaseModel):
    stream_type: str  # "group" or "personal"
    owner_id: int

class CreateStreamResponse(BaseModel):
    stream_id: str
    deep_link: str

class JoinStreamRequest(BaseModel):
    stream_id: str
    user: TelegramUser