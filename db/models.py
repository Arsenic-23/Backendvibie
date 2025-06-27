# db/models.py

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class User(SQLModel, table=True):
    user_id: str = Field(primary_key=True, index=True)
    name: str
    profile_pic: Optional[str] = None
    current_stream_id: Optional[str] = Field(default=None, foreign_key="stream.stream_id")


class Song(SQLModel, table=True):
    song_id: str = Field(primary_key=True, index=True)
    title: str
    artist: Optional[str]
    duration: Optional[int]  # seconds
    thumbnail_url: Optional[str] = None
    audio_url: Optional[str] = None

    # ✅ FIX: add stream_id to support stream-based queueing
    stream_id: Optional[str] = Field(default=None, foreign_key="stream.stream_id")


class Stream(SQLModel, table=True):
    stream_id: str = Field(primary_key=True, index=True)
    now_playing_song_id: Optional[str] = Field(default=None, foreign_key="song.song_id")
    start_time: Optional[datetime] = None