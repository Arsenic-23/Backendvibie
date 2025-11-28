# utils/notify.py
import asyncio
from typing import Any


async def notify_stream(stream_id: str, event: str, payload: Any):
    """
    Broadcast a JSON event to all connected clients within stream_id.

    Expects a ws.manager.connection_manager with a broadcast method:
      await connection_manager.broadcast(stream_id, message)
    If not present, this is a no-op.
    """
    try:
        from ws.manager import connection_manager  # type: ignore
    except Exception:
        # No manager defined, nothing to do
        return

    message = {"event": event, "data": payload}
    try:
        await connection_manager.broadcast(stream_id, message)
    except Exception:
        return


def notify_stream_background(stream_id: str, event: str, payload: Any):
    """
    Fire-and-forget wrapper for notify_stream from sync endpoints.
    Uses the running event loop if available.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        loop.create_task(notify_stream(stream_id, event, payload))
