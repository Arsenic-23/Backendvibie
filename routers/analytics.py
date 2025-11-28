# routers/analytics.py
from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func
from db.database import get_session
from db.models import Stream, StreamParticipant, User
from utils.auth import verify_firebase_token

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def scalar(session: Session, query):
    """
    Safe universal scalar extractor:
    returns first column of first row or 0.
    """
    result = session.exec(query).all()
    if not result:
        return 0
    val = result[0]
    if isinstance(val, (list, tuple)):
        return val[0]
    return val


@router.get("/summary")
def get_summary(
    session: Session = Depends(get_session),
    firebase_uid: str = Depends(verify_firebase_token),
):
    total_streams = scalar(
        session, select(func.count(Stream.stream_id))
    )

    total_users = scalar(
        session, select(func.count(User.user_id))
    )

    active_stream_participations = scalar(
        session, select(func.count(StreamParticipant.user_id))
    )

    return {
        "total_streams": total_streams,
        "total_users": total_users,
        "active_stream_participations": active_stream_participations,
    }


@router.get("/stream/{stream_id}")
def analytics_for_stream(
    stream_id: str,
    session: Session = Depends(get_session),
    firebase_uid: str = Depends(verify_firebase_token),
):
    total_participants = scalar(
        session,
        select(func.count(StreamParticipant.user_id)).where(
            StreamParticipant.stream_id == stream_id
        )
    )

    total_admins = scalar(
        session,
        select(func.count(StreamParticipant.user_id)).where(
            (StreamParticipant.stream_id == stream_id)
            & (StreamParticipant.is_admin == True)
        )
    )

    return {
        "stream_id": stream_id,
        "total_participants": total_participants,
        "total_admins": total_admins,
    }


@router.get("/top-streams")
def top_streams(
    session: Session = Depends(get_session),
    firebase_uid: str = Depends(verify_firebase_token),
):
    rows = session.exec(
        select(
            StreamParticipant.stream_id,
            func.count(StreamParticipant.user_id)
        )
        .group_by(StreamParticipant.stream_id)
        .order_by(func.count(StreamParticipant.user_id).desc())
    ).all()

    return [
        {"stream_id": r[0], "participant_count": r[1]}
        for r in rows
    ]


@router.get("/user/{user_id}")
def analytics_for_user(
    user_id: str,
    session: Session = Depends(get_session),
    firebase_uid: str = Depends(verify_firebase_token),
):
    streams_joined = scalar(
        session,
        select(func.count(StreamParticipant.stream_id)).where(
            StreamParticipant.user_id == user_id
        )
    )

    streams_hosted = scalar(
        session,
        select(func.count(Stream.stream_id)).where(
            Stream.host_id == user_id
        )
    )

    return {
        "user_id": user_id,
        "streams_joined": streams_joined,
        "streams_hosted": streams_hosted,
    }
