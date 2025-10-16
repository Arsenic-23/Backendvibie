import asyncio
from typing import Any

async def notify_stream(stream_id: str, event: str, payload: Any):
    """
    Broadcast a JSON event to all connected clients within stream_id.
    This attempts to call your websocket manager's broadcast method:
      from ws.manager import connection_manager
      await connection_manager.broadcast(stream_id, message)
    If no manager exists, this becomes a no-op.

    Keep this signature async so FastAPI BackgroundTasks can call it.
    """
    try:
        from ws.manager import connection_manager  
        message = {"event": event, "data": payload}
        await connection_manager.broadcast(stream_id, message)
    except Exception:
        return
