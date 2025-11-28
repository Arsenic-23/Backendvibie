# utils/auth.py
from fastapi import Header, HTTPException
from firebase_admin import auth


def verify_firebase_token(authorization: str = Header(...)) -> str:
    """
    Extracts Firebase ID token from Authorization header and verifies it.
    Returns Firebase UID if valid.

    Header format:
      Authorization: Bearer <ID_TOKEN>
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    id_token = authorization.split(" ", 1)[1].strip()

    try:
        decoded = auth.verify_id_token(id_token)
        return decoded["uid"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired Firebase ID token")
