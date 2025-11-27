# utils/memory.py
from typing import Dict, List, Any

# In-memory list of active users per stream (for presence)
active_vibers: Dict[str, List[Dict]] = {}

# WebSocket connections for each stream (for broadcasting)
# Each value is a list of WebSocket objects.
active_connections: Dict[str, List[Any]] = {}