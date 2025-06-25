# utils/memory.py

from typing import Dict, List

# In-memory list of active users per stream
active_vibers: Dict[str, List[Dict]] = {}

# WebSocket connections for each stream (for broadcasting)
active_connections: Dict[str, List] = {}

def add_viber(stream_id: str, user: Dict):
    """Add a user to a stream's vibers list."""
    if stream_id not in active_vibers:
        active_vibers[stream_id] = []

    if not any(u["user_id"] == user["user_id"] for u in active_vibers[stream_id]):
        active_vibers[stream_id].append(user)

def remove_viber(stream_id: str, user_id: str):
    """Remove a user from a stream's vibers list."""
    if stream_id in active_vibers:
        active_vibers[stream_id] = [
            u for u in active_vibers[stream_id] if u["user_id"] != user_id
        ]
        if not active_vibers[stream_id]:
            del active_vibers[stream_id]