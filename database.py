from typing import Dict, List
from collections import defaultdict
from fastapi.websockets import WebSocket

# In-memory store of stream data and WebSocket connections
streams: Dict[str, List[dict]] = defaultdict(list)  # stream_id -> list of user dicts
connections: Dict[str, List[WebSocket]] = defaultdict(list)  # stream_id -> list of sockets

def add_user_to_stream(stream_id: str, user: dict):
    if not any(u['user_id'] == user['user_id'] for u in streams[stream_id]):
        streams[stream_id].append(user)

def remove_user_from_stream(stream_id: str, user_id: int):
    streams[stream_id] = [u for u in streams[stream_id] if u['user_id'] != user_id]

def get_users_in_stream(stream_id: str) -> List[dict]:
    return streams[stream_id]