# routers/stream.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from db.database import get_session
from db.models import Stream, Song, User
from utils.memory import active_vibers
from datetime import datetime

router = APIRouter()

@router.get("/{stream_id}")
def get_stream_data(stream_id: str, session: Session = Depends(get_session)):
    # Fetch stream
    stream = session.exec(select(Stream).where(Stream.stream_id == stream_id)).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    # Fetch now playing song
    now_playing = None
    if stream.now_playing_song_id:
        song = session.exec(select(Song).where(Song.song_id == stream.now_playing_song_id)).first()
        if song:
            now_playing = {
                "song_id": song.song_id,
                "title": song.title,
                "artist": song.artist,
                "thumbnail_url": song.thumbnail_url,
                "duration": song.duration,
                "start_time": stream.start_time.isoformat() if stream.start_time else None
            }

    # Fetch active vibers (from memory)
    vibers = active_vibers.get(stream_id, [])

    return {
        "stream_id": stream.stream_id,
        "now_playing": now_playing,
        "vibers": vibers
    }

@router.post("/{stream_id}/now_playing")
def update_now_playing(stream_id: str, song_id: str, session: Session = Depends(get_session)):
    stream = session.exec(select(Stream).where(Stream.stream_id == stream_id)).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    stream.now_playing_song_id = song_id
    stream.start_time = datetime.utcnow()

    session.add(stream)
    session.commit()
    session.refresh(stream)

    return {"message": "Now playing updated", "start_time": stream.start_time.isoformat()}
