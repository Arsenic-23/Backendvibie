from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlmodel import Session, select
from db.database import get_session
from db.models import Stream, Song, User
from utils.memory import active_vibers  
from datetime import datetime
import uuid
from typing import Optional, List, Dict

router = APIRouter()


def _get_user(session: Session, user_id: str) -> Optional[User]:
    return session.exec(select(User).where(User.user_id == user_id)).first()


def _get_stream(session: Session, stream_id: str) -> Optional[Stream]:
    return session.exec(select(Stream).where(Stream.stream_id == stream_id)).first()


def _is_admin_in_memory(stream_id: str, user_id: str) -> bool:
    vibers = active_vibers.get(stream_id, [])
    for v in vibers:
        if v.get("user_id") == user_id and v.get("role") in ("admin", "host"):
            return True
    return False


@router.post("/create")
def create_stream(
    user_id: str = Body(..., embed=True),
    title: Optional[str] = Body(None, embed=True),
    session: Session = Depends(get_session),
):
    """
    Create a new stream and assign the creating user as admin/host.
    Request body:
    {
      "user_id": "u123",
      "title": "Chill Beats"
    }
    """
    user = _get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stream_id = str(uuid.uuid4())

    stream = Stream(stream_id=stream_id)
    session.add(stream)

    user.current_stream_id = stream_id
    session.add(user)

    session.commit()
    session.refresh(stream)
    session.refresh(user)

    active_vibers[stream_id] = [
        {
            "user_id": user.user_id,
            "name": user.name,
            "profile_pic": user.profile_pic,
            "role": "host",  
            "joined_at": datetime.utcnow().isoformat(),
        }
    ]

    return {
        "message": "Stream created",
        "stream_id": stream.stream_id,
        "host": {"user_id": user.user_id, "name": user.name},
    }


@router.post("/{stream_id}/join")
def join_stream(
    stream_id: str,
    user_id: str = Body(..., embed=True),
    session: Session = Depends(get_session),
):
    """
    Add a user to an existing stream.
    Request:
    { "user_id": "u123" }
    """
    stream = _get_stream(session, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    user = _get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.current_stream_id = stream_id
    session.add(user)
    session.commit()
    session.refresh(user)

    vibers = active_vibers.get(stream_id, [])
    exists = any(v.get("user_id") == user.user_id for v in vibers)
    if not exists:
        vibers.append(
            {
                "user_id": user.user_id,
                "name": user.name,
                "profile_pic": user.profile_pic,
                "role": "listener",
                "joined_at": datetime.utcnow().isoformat(),
            }
        )
        active_vibers[stream_id] = vibers

    return {
        "message": "Joined stream",
        "stream_id": stream_id,
        "user": {"user_id": user.user_id, "name": user.name},
    }


@router.post("/{stream_id}/leave")
def leave_stream(
    stream_id: str,
    user_id: str = Body(..., embed=True),
    session: Session = Depends(get_session),
):
    """
    Remove a user from stream's active vibers and clear their current_stream_id.
    Request:
    { "user_id": "u123" }
    """
    stream = _get_stream(session, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    user = _get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.current_stream_id == stream_id:
        user.current_stream_id = None
        session.add(user)
        session.commit()
        session.refresh(user)

    vibers = active_vibers.get(stream_id, [])
    new_vibers = [v for v in vibers if v.get("user_id") != user.user_id]
    if new_vibers:
        active_vibers[stream_id] = new_vibers
    else:
        active_vibers.pop(stream_id, None)

    return {"message": "Left stream", "stream_id": stream_id, "user_id": user.user_id}


@router.get("/{stream_id}/users")
def list_stream_users(stream_id: str):
    """
    Return the list of active vibers (participants) in a stream.
    """
    vibers = active_vibers.get(stream_id, [])
    return {"stream_id": stream_id, "users": vibers}


class KickRequest(dict):
    """
    simple shaped dictionary fallback for FastAPI/Doc readability.
    Not strictly necessary; we accept body fields via Body(...) below.
    """
    pass


@router.post("/{stream_id}/kick")
def kick_user(
    stream_id: str,
    admin_user_id: str = Body(..., embed=True),
    target_user_id: str = Body(..., embed=True),
    block: bool = Body(False, embed=True),
    session: Session = Depends(get_session),
):
    """
    Admin-only endpoint to remove a user from a stream. Optionally block them (in-memory).
    Body:
    {
      "admin_user_id": "u_admin",
      "target_user_id": "u_to_kick",
      "block": false
    }
    """
    stream = _get_stream(session, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    if not _is_admin_in_memory(stream_id, admin_user_id):
        raise HTTPException(status_code=403, detail="Only admins can kick users")

    target = _get_user(session, target_user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target user not found")

    vibers = active_vibers.get(stream_id, [])
    new_vibers = [v for v in vibers if v.get("user_id") != target_user_id]
    active_vibers[stream_id] = new_vibers

    if target.current_stream_id == stream_id:
        target.current_stream_id = None
        session.add(target)
        session.commit()
        session.refresh(target)

    try:
        from utils.memory import blocked_vibers
    except Exception:
        blocked_vibers = globals().get("blocked_vibers")
        if blocked_vibers is None:
            blocked_vibers = {}
            globals()["blocked_vibers"] = blocked_vibers

    if block:
        blocked = blocked_vibers.get(stream_id, set())
        if isinstance(blocked, set):
            blocked.add(target_user_id)
        else:
            blocked = set(blocked)
            blocked.add(target_user_id)
        blocked_vibers[stream_id] = blocked

    return {"message": "User kicked", "stream_id": stream_id, "target_user_id": target_user_id}


@router.delete("/{stream_id}/delete")
def delete_stream(
    stream_id: str,
    admin_user_id: str = Body(..., embed=True),
    session: Session = Depends(get_session),
):
    """
    Admin-only: delete a stream completely from DB and clear in-memory state.
    Body:
    { "admin_user_id": "u_admin" }
    """
    stream = _get_stream(session, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    if not _is_admin_in_memory(stream_id, admin_user_id):
        raise HTTPException(status_code=403, detail="Only admins can delete a stream")

    vibers = active_vibers.get(stream_id, [])
    for v in vibers:
        try:
            u = _get_user(session, v.get("user_id"))
            if u and u.current_stream_id == stream_id:
                u.current_stream_id = None
                session.add(u)
        except Exception:
            continue

    session.delete(stream)
    session.commit()

    active_vibers.pop(stream_id, None)
    try:
        from utils.memory import blocked_vibers
        blocked_vibers.pop(stream_id, None)
    except Exception:
        pass

    return {"message": "Stream deleted", "stream_id": stream_id}
