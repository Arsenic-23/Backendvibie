from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from db.database import get_session
from db.models import Song, Stream
from typing import Optional
from pydantic import BaseModel

router = APIRouter()


# ===============================
# Request Models
# ===============================
class AddSongRequest(BaseModel):
    stream_id: str
    song_id: str
    title: str
    artist: Optional[str] = None
    duration: Optional[int] = None
    thumbnail_url: Optional[str] = None
    audio_url: Optional[str] = None


# ===============================
# Add song to queue
# ===============================
@router.post("/add")
def add_song_to_queue(data: AddSongRequest, session: Session = Depends(get_session)):
    # Check or create song in DB
    song = session.exec(select(Song).where(Song.song_id == data.song_id)).first()
    if not song:
        song = Song(
            song_id=data.song_id,
            title=data.title,
            artist=data.artist,
            duration=data.duration,
            thumbnail_url=data.thumbnail_url,
            audio_url=data.audio_url,
            stream_id=data.stream_id
        )
        session.add(song)
        session.commit()

    # Fetch stream
    stream = session.exec(select(Stream).where(Stream.stream_id == data.stream_id)).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    # Append song to stream queue (persistent)
    stream.queue.append(data.song_id)
    session.add(stream)
    session.commit()
    session.refresh(stream)

    return {"message": "Song added to queue", "queue": stream.queue}


# ===============================
# Get full queue
# ===============================
@router.get("/{stream_id}")
def get_queue(stream_id: str, session: Session = Depends(get_session)):
    stream = session.exec(select(Stream).where(Stream.stream_id == stream_id)).first()
    if not stream or not stream.queue:
        return {"queue": []}

    # Fetch songs from DB and preserve order
    songs = session.exec(select(Song).where(Song.song_id.in_(stream.queue))).all()
    song_dict = {s.song_id: s for s in songs}
    ordered_queue = [song_dict[sid] for sid in stream.queue if sid in song_dict]

    return {"queue": ordered_queue}


# ===============================
# Pop first song from queue
# ===============================
@router.delete("/{stream_id}/pop")
def pop_song(stream_id: str, session: Session = Depends(get_session)):
    stream = session.exec(select(Stream).where(Stream.stream_id == stream_id)).first()
    if not stream or not stream.queue:
        raise HTTPException(status_code=404, detail="Queue empty")

    removed_song_id = stream.queue.pop(0)
    session.add(stream)
    session.commit()
    session.refresh(stream)

    return {"message": "Song removed from queue", "removed_song_id": removed_song_id}
