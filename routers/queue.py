# routers/queue.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from db.database import get_session
from db.models import Song
from typing import List, Optional

# In-memory queue per stream
queue_map = {}

router = APIRouter()

class AddSongRequest(BaseModel):
    stream_id: str
    song_id: str
    title: str
    artist: Optional[str] = None
    duration: Optional[int] = None
    thumbnail_url: Optional[str] = None
    audio_url: Optional[str] = None

@router.post("/add")
def add_song_to_queue(data: AddSongRequest, session: Session = Depends(get_session)):
    # Save song to DB if not exists
    song = session.exec(select(Song).where(Song.song_id == data.song_id)).first()
    if not song:
        song = Song(
            song_id=data.song_id,
            title=data.title,
            artist=data.artist,
            duration=data.duration,
            thumbnail_url=data.thumbnail_url,
            audio_url=data.audio_url
        )
        session.add(song)
        session.commit()

    # Add to in-memory queue
    if data.stream_id not in queue_map:
        queue_map[data.stream_id] = []
    queue_map[data.stream_id].append(data.song_id)

    return {"message": "Song added to queue", "queue": queue_map[data.stream_id]}

@router.get("/{stream_id}")
def get_queue(stream_id: str, session: Session = Depends(get_session)):
    # Return full song info from queue
    song_ids = queue_map.get(stream_id, [])
    if not song_ids:
        return {"queue": []}

    songs = session.exec(select(Song).where(Song.song_id.in_(song_ids))).all()
    # Preserve order
    song_dict = {song.song_id: song for song in songs}
    ordered_queue = [song_dict[sid] for sid in song_ids if sid in song_dict]

    return {"queue": ordered_queue}
