# db/models.py
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, ForeignKey
from sqlalchemy.types import JSON as SQLJSON

class User(SQLModel, table=True):
    """
    User identified by Firebase UID.
    user_id is the Firebase uid (no Telegram).
    """
    user_id: str = Field(primary_key=True, index=True) 
    name: str
    username: Optional[str] = None
    profile_pic: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Song(SQLModel, table=True):
    """
    Song metadata fetched via ytdlp.
    song_id is typically the YouTube video ID.
    """
    song_id: str = Field(primary_key=True, index=True)
    title: str
    artist: Optional[str] = None
    duration: Optional[int] = None 
    thumbnail_url: Optional[str] = None
    audio_url: Optional[str] = None  

class Stream(SQLModel, table=True):
    """
    A listening stream/room.
    stream_id is the “code” you share (string).
    """
    stream_id: str = Field(primary_key=True, index=True)

    host_id: str = Field(foreign_key="user.user_id")
    visibility: Optional[str] = Field(default="public") 
    title: Optional[str] = None

    current_queue_item_id: Optional[int] = Field(
        default=None, foreign_key="streamqueueitem.id"
    )
    playback_status: str = Field(default="stopped") 
    playback_position_ms: int = Field(default=0)    
    playback_updated_at: Optional[datetime] = None   

    start_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class StreamParticipant(SQLModel, table=True):
    """
    Persistent membership in a stream.
    """
    stream_id: str = Field(foreign_key="stream.stream_id", primary_key=True)
    user_id: str = Field(foreign_key="user.user_id", primary_key=True)
    is_admin: bool = Field(default=False)

    joined_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)

class StreamQueueItem(SQLModel, table=True):
    """
    Each row is one song in a stream's queue.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    stream_id: str = Field(foreign_key="stream.stream_id", index=True)
    song_id: str = Field(foreign_key="song.song_id", index=True)

    position: int = Field(index=True)  
    status: str = Field(default="queued")  

    added_by: str = Field(foreign_key="user.user_id")
    added_at: datetime = Field(default_factory=datetime.utcnow)

    extra: Optional[dict] = Field(default=None, sa_column=Column(SQLJSON))
