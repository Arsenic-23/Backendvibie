# routers/stream.py

from fastapi import APIRouter, Depends, HTTPException, status, Body, BackgroundTasks
from sqlmodel import Session, select
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from db.database import get_session
from db.models import Stream, Song, User
from utils.memory import active_vibers, blocked_vibers

# try import notify_stream, fallback to safe async no-op
try:
    from ws.events import notify_stream  # async function (stream_id, event, payload)
except Exception:
    async def notify_stream(stream_id: str, event: str, payload: Any):
        return

router = APIRouter()


# ---------- helpers ----------

def _get_user(session: Session, user_id: str) -> Optional[User]:
    return session.exec(select(User).where(User.user_id == user_id)).first()


def _get_stream(session: Session, stream_id: str) -> Optional[Stream]:
    return session.exec(select(Stream).where(Stream.stream_id == stream_id)).first()


def _is_admin(session: Session, stream: Stream, user_id: str) -> bool:
    if not stream:
        return False
    return user_id in (stream.admins or [])


def _add_active_viber(stream_id: str, user: User, role: str = "listener"):
    vibers = active_vibers.get(stream_id, [])
    if not any(v.get("user_id") == user.user_id for v in vibers):
        vibers.append({
            "user_id": user.user_id,
            "name": user.name,
            "username": user.username,
            "profile_pic": user.profile_pic,
            "role": role,
            "joined_at": datetime.utcnow().isoformat(),
        })
    active_vibers[stream_id] = vibers


def _remove_active_viber(stream_id: str, user_id: str):
    vibers = active_vibers.get(stream_id, [])
    new_vibers = [v for v in vibers if v.get("user_id") != user_id]
    if new_vibers:
        active_vibers[stream_id] = new_vibers
    else:
        active_vibers.pop(stream_id, None)


def _expand_participants(session: Session, stream: Stream) -> List[Dict[str, Any]]:
    """
    Return an expanded participants list with basic user info and role.
    """
    out = []
    for uid in (stream.participants or []):
        u = _get_user(session, uid)
        role = "listener"
        if stream.admins and uid in stream.admins:
            role = "admin"
        if u:
            out.append({
                "user_id": u.user_id,
                "name": u.name,
                "username": u.username,
                "profile_pic": u.profile_pic,
                "role": role,
            })
        else:
            # fallback if user not present in DB
            out.append({"user_id": uid, "name": None, "username": None, "profile_pic": None, "role": role})
    return out


# ---------- endpoints ----------

@router.post("/create", status_code=201)
def create_stream(
    background_tasks: BackgroundTasks,
    user_id: str = Body(..., embed=True),
    title: Optional[str] = Body(None, embed=True),
    visibility: Optional[str] = Body("public", embed=True),
    session: Session = Depends(get_session),
):
    """
    Create a new stream and assign the creating user as admin/host.
    Body:
    { "user_id": "u123", "title": "Chill Beats", "visibility": "public" }
    """
    user = _get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # create unique short stream id
    stream_id = str(uuid.uuid4())[:8]

    stream = Stream(
        stream_id=stream_id,
        title=title,
        visibility=visibility,
        admins=[user.user_id],
        participants=[user.user_id],
        blocked=[],
        queue=[],
        now_playing_song_id=None,
        start_time=None,
    )

    session.add(stream)
    user.current_stream_id = stream_id
    session.add(user)
    session.commit()
    session.refresh(stream)
    session.refresh(user)

    # initialize in-memory presence
    _add_active_viber(stream_id, user, role="admin")

    # notify via WS (background)
    background_tasks.add_task(notify_stream, stream_id, "stream_created", {"stream_id": stream_id, "host": {"user_id": user.user_id, "name": user.name}})

    return {"message": "Stream created", "stream_id": stream.stream_id, "host": {"user_id": user.user_id, "name": user.name}}


@router.post("/join", status_code=200)
def join_stream(
    background_tasks: BackgroundTasks,
    user_id: str = Body(..., embed=True),
    stream_id: str = Body(..., embed=True),
    session: Session = Depends(get_session),
):
    """
    Join an existing stream.
    Body:
    { "user_id": "u123", "stream_id": "abcd1234" }
    """
    user = _get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stream = _get_stream(session, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    # Check DB blocked list first
    if (stream.blocked or []) and user_id in (stream.blocked or []):
        raise HTTPException(status_code=403, detail="You are blocked from this stream")

    # Add to participants persistently
    if user_id not in (stream.participants or []):
        stream.participants.append(user_id)
    # ensure admin list exists
    if stream.admins is None:
        stream.admins = []

    # update user current_stream_id
    user.current_stream_id = stream_id
    session.add(stream)
    session.add(user)
    session.commit()
    session.refresh(stream)
    session.refresh(user)

    # update in-memory presence
    role = "admin" if user_id in (stream.admins or []) else "listener"
    _add_active_viber(stream_id, user, role=role)

    # Broadcast user joined
    background_tasks.add_task(notify_stream, stream_id, "user_joined", {"user_id": user.user_id, "name": user.name, "role": role})

    return {
        "message": "Joined stream",
        "stream_id": stream.stream_id,
        "participants": _expand_participants(session, stream),
    }


@router.post("/{stream_id}/leave", status_code=200)
def leave_stream(
    background_tasks: BackgroundTasks,
    stream_id: str,
    user_id: str = Body(..., embed=True),
    session: Session = Depends(get_session),
):
    """
    Leave the stream and clear user's current_stream_id.
    Body: { "user_id": "u123" }
    """
    stream = _get_stream(session, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    user = _get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # remove from participants persistently
    if stream.participants and user_id in stream.participants:
        stream.participants = [u for u in stream.participants if u != user_id]

    # if user was admin, we might keep them in admins list unless explicit revoke
    # update user's current_stream_id
    if user.current_stream_id == stream_id:
        user.current_stream_id = None

    session.add(stream)
    session.add(user)
    session.commit()
    session.refresh(stream)
    session.refresh(user)

    # remove in-memory presence
    _remove_active_viber(stream_id, user_id)

    # if no participants left, clear in-memory presence dict
    if not (stream.participants or []):
        active_vibers.pop(stream_id, None)

    # broadcast user left
    background_tasks.add_task(notify_stream, stream_id, "user_left", {"user_id": user_id})

    return {"message": "Left stream", "stream_id": stream_id, "user_id": user_id}


@router.get("/{stream_id}", status_code=200)
def get_stream_data(stream_id: str, session: Session = Depends(get_session)):
    """
    Return stream info: now_playing, queue, participants (expanded), admins, blocked (ids).
    """
    stream = _get_stream(session, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

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
                "start_time": stream.start_time.isoformat() if stream.start_time else None,
            }

    participants = _expand_participants(session, stream)
    vibers = active_vibers.get(stream_id, [])

    return {
        "stream_id": stream.stream_id,
        "title": stream.title,
        "visibility": stream.visibility,
        "admins": stream.admins or [],
        "participants": participants,
        "blocked": stream.blocked or [],
        "queue": stream.queue or [],
        "now_playing": now_playing,
        "active_vibers": vibers,
        "created_at": stream.created_at.isoformat() if stream.created_at else None
    }


@router.get("/{stream_id}/users", status_code=200)
def list_stream_users(stream_id: str, session: Session = Depends(get_session)):
    """
    Return expanded participant list (DB-based).
    """
    stream = _get_stream(session, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    participants = _expand_participants(session, stream)
    return {"stream_id": stream_id, "participants": participants}


@router.post("/{stream_id}/now_playing", status_code=200)
def update_now_playing(
    background_tasks: BackgroundTasks,
    stream_id: str,
    song_id: str = Body(..., embed=True),
    user_id: Optional[str] = Body(None, embed=True),
    session: Session = Depends(get_session),
):
    """
    Update currently playing song. By default require that the caller is admin (if user_id provided).
    Body: { "song_id": "yt123", "user_id": "u_admin" }
    """
    stream = _get_stream(session, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    # If a user_id was provided, check admin rights
    if user_id:
        if not _is_admin(session, stream, user_id):
            raise HTTPException(status_code=403, detail="Only admins can change now playing")

    # Validate song exists optionally
    song = session.exec(select(Song).where(Song.song_id == song_id)).first()
    if not song:
        # you may still allow external song ids; here we allow but warn
        pass

    stream.now_playing_song_id = song_id
    stream.start_time = datetime.utcnow()
    session.add(stream)
    session.commit()
    session.refresh(stream)

    # notify via websocket
    payload = {
        "song_id": song_id,
        "start_time": stream.start_time.isoformat()
    }
    background_tasks.add_task(notify_stream, stream_id, "now_playing", payload)

    return {"message": "Now playing updated", "song_id": song_id, "start_time": stream.start_time.isoformat()}


@router.post("/{stream_id}/kick", status_code=200)
def kick_user(
    background_tasks: BackgroundTasks,
    stream_id: str,
    admin_user_id: str = Body(..., embed=True),
    target_user_id: str = Body(..., embed=True),
    block: bool = Body(False, embed=True),
    session: Session = Depends(get_session),
):
    """
    Admin-only: remove (and optionally block) a user from the stream.
    Body: { "admin_user_id": "u_admin", "target_user_id": "u_bad", "block": true }
    """
    stream = _get_stream(session, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    if not _is_admin(session, stream, admin_user_id):
        raise HTTPException(status_code=403, detail="Only admins can kick users")

    target = _get_user(session, target_user_id)
    # Remove from participants persistently
    if stream.participants and target_user_id in stream.participants:
        stream.participants = [u for u in stream.participants if u != target_user_id]

    # Add to blocked if requested (persist)
    if block:
        if stream.blocked is None:
            stream.blocked = []
        if target_user_id not in stream.blocked:
            stream.blocked.append(target_user_id)

        # also maintain in-memory blocked_vibers set for fast check
        s = blocked_vibers.get(stream_id, set())
        s.add(target_user_id)
        blocked_vibers[stream_id] = s

    # Clear target.current_stream_id
    if target and target.current_stream_id == stream_id:
        target.current_stream_id = None
        session.add(target)

    session.add(stream)
    session.commit()
    session.refresh(stream)

    # remove in-memory presence
    _remove_active_viber(stream_id, target_user_id)

    # broadcast
    background_tasks.add_task(notify_stream, stream_id, "user_kicked", {"target_user_id": target_user_id, "by": admin_user_id, "blocked": block})

    return {"message": "User kicked", "target_user_id": target_user_id, "blocked": block}


@router.post("/{stream_id}/authorize", status_code=200)
def authorize_admin(
    background_tasks: BackgroundTasks,
    stream_id: str,
    admin_user_id: str = Body(..., embed=True),
    target_user_id: str = Body(..., embed=True),
    action: str = Body("add", embed=True),  # "add" or "remove"
    session: Session = Depends(get_session),
):
    """
    Admin-only: grant/remove admin role for a participant.
    Body: { "admin_user_id": "u_admin", "target_user_id": "u2", "action": "add" }
    """
    stream = _get_stream(session, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    if not _is_admin(session, stream, admin_user_id):
        raise HTTPException(status_code=403, detail="Only admins can authorize others")

    if stream.admins is None:
        stream.admins = []

    if action == "add":
        if target_user_id not in stream.admins:
            stream.admins.append(target_user_id)
    elif action == "remove":
        stream.admins = [u for u in (stream.admins or []) if u != target_user_id]
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    session.add(stream)
    session.commit()
    session.refresh(stream)

    # update in-memory role for active viber if present
    vibers = active_vibers.get(stream_id, [])
    for v in vibers:
        if v.get("user_id") == target_user_id:
            v["role"] = "admin" if action == "add" else "listener"
    active_vibers[stream_id] = vibers

    background_tasks.add_task(notify_stream, stream_id, "admin_updated", {"target_user_id": target_user_id, "action": action, "by": admin_user_id})

    return {"message": "Admin updated", "target_user_id": target_user_id, "action": action}


@router.delete("/{stream_id}/delete", status_code=200)
def delete_stream(
    background_tasks: BackgroundTasks,
    stream_id: str,
    admin_user_id: str = Body(..., embed=True),
    session: Session = Depends(get_session),
):
    """
    Admin-only: delete the stream and clear participants' current_stream_id.
    Body: { "admin_user_id": "u_admin" }
    """
    stream = _get_stream(session, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    if not _is_admin(session, stream, admin_user_id):
        raise HTTPException(status_code=403, detail="Only admins can delete the stream")

    # Clear current_stream_id for participants
    for uid in (stream.participants or []):
        u = _get_user(session, uid)
        if u and u.current_stream_id == stream_id:
            u.current_stream_id = None
            session.add(u)

    # delete stream
    session.delete(stream)
    session.commit()

    # clear in-memory
    active_vibers.pop(stream_id, None)
    blocked_vibers.pop(stream_id, None) if stream_id in blocked_vibers else None

    # broadcast
    background_tasks.add_task(notify_stream, stream_id, "stream_deleted", {"stream_id": stream_id, "by": admin_user_id})

    return {"message": "Stream deleted", "stream_id": stream_id}
