from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from db.database import get_session
from db.models import Song
from typing import Optional
from pydantic import BaseModel

router = APIRouter()

# In-memory queues
queue_map = {}

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

    queue = queue_map.setdefault(data.stream_id, [])
    queue.append(data.song_id)
    return {"message": "Song added to queue", "queue": queue}

@router.get("/{stream_id}")
def get_queue(stream_id: str, session: Session = Depends(get_session)):
    song_ids = queue_map.get(stream_id, [])
    if not song_ids:
        return {"queue": []}
    songs = session.exec(select(Song).where(Song.song_id.in_(song_ids))).all()
    song_dict = {s.song_id: s for s in songs}
    ordered_queue = [song_dict[sid] for sid in song_ids if sid in song_dict]
    return {"queue": ordered_queue}

@router.delete("/{stream_id}/pop")
def pop_song(stream_id: str):
    if stream_id not in queue_map or not queue_map[stream_id]:
        raise HTTPException(status_code=404, detail="Queue empty")
    removed = queue_map[stream_id].pop(0)
    return {"message": "Song removed", "removed_song_id": removed}
