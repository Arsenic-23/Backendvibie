from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime
from sqlalchemy import Column
from sqlalchemy.types import JSON as SQLJSON


# ===============================
# User Model
# ===============================
class User(SQLModel, table=True):
    user_id: str = Field(primary_key=True, index=True)
    name: str
    username: Optional[str] = None
    profile_pic: Optional[str] = None
    current_stream_id: Optional[str] = Field(default=None, foreign_key="stream.stream_id")


# ===============================
# Song Model
# ===============================
class Song(SQLModel, table=True):
    song_id: str = Field(primary_key=True, index=True)
    title: str
    artist: Optional[str] = None
    duration: Optional[int] = None  # seconds
    thumbnail_url: Optional[str] = None
    audio_url: Optional[str] = None
    # Optional association to stream
    stream_id: Optional[str] = Field(default=None, foreign_key="stream.stream_id")


# ===============================
# Stream Model
# ===============================
class Stream(SQLModel, table=True):
    """
    Stream model with persistent admins, participants, blocked users, and queue.
    JSON columns allow easy storage of lists.
    """
    stream_id: str = Field(primary_key=True, index=True)
    now_playing_song_id: Optional[str] = Field(default=None, foreign_key="song.song_id")
    start_time: Optional[datetime] = None

    # Persistent lists stored as JSON columns
    admins: List[str] = Field(default_factory=list, sa_column=Column(SQLJSON))
    participants: List[str] = Field(default_factory=list, sa_column=Column(SQLJSON))
    blocked: List[str] = Field(default_factory=list, sa_column=Column(SQLJSON))
    queue: List[str] = Field(default_factory=list, sa_column=Column(SQLJSON))

    visibility: Optional[str] = Field(default="public")  # public/private
    title: Optional[str] = Field(default=None)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
