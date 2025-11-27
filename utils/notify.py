# utils/notify.py
import asyncio
from typing import Any
from ws.websocket import broadcast_to_stream


async def notify_stream(stream_id: str, event: str, payload: Any):
    """
    Broadcast an event to all connected clients in the stream.
    event -> becomes "type"
    payload -> becomes "payload"
    """
    message = {"type": event, "payload": payload}
    await broadcast_to_stream(stream_id, message)


def notify_stream_background(stream_id: str, event: str, payload: Any):
    """
    Helper for sync endpoints: schedule notify_stream.
    """
    asyncio.create_task(notify_stream(stream_id, event, payload))