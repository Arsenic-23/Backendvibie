from typing import Dict, List
from collections import defaultdict
from fastapi.websockets import WebSocket

# In-memory store of stream users and WebSocket connections
streams: Dict[str, List[dict]] = defaultdict(list)  # stream_id -> list of user dicts
connections: Dict[str, List[WebSocket]] = defaultdict(list)  # stream_id -> list of WebSocket connections

def normalize_user(user_data: dict) -> dict:
    return {
        "user_id": user_data["user_id"],
        "name": user_data["first_name"],
        "profile_pic": user_data.get("photo_url", "")
    }

def add_user_to_stream(stream_id: str, raw_user: dict):
    user = normalize_user(raw_user)
    if not any(u["user_id"] == user["user_id"] for u in streams[stream_id]):
        streams[stream_id].append(user)

def remove_user_from_stream(stream_id: str, user_id: int):
    streams[stream_id] = [u for u in streams[stream_id] if u["user_id"] != user_id]

def get_users_in_stream(stream_id: str) -> List[dict]:
    return streams[stream_id]

def register_connection(stream_id: str, socket: WebSocket):
    if socket not in connections[stream_id]:
        connections[stream_id].append(socket)

def unregister_connection(stream_id: str, socket: WebSocket):
    if socket in connections[stream_id]:
        connections[stream_id].remove(socket)

def get_connections(stream_id: str) -> List[WebSocket]:
    return connections[stream_id]