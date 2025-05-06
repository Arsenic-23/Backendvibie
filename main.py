# main.py

from fastapi import FastAPI, WebSocket
from routers import stream as stream_router
from sockets.stream_ws import stream_websocket_endpoint

app = FastAPI()

# Register REST API routes
app.include_router(stream_router.router, prefix="/stream", tags=["Stream"])

# WebSocket endpoint for real-time updates
@app.websocket("/ws/stream/{stream_id}/{user_id}/{username}")
async def stream_ws(websocket: WebSocket, stream_id: str, user_id: int, username: str):
    await stream_websocket_endpoint(websocket, stream_id, user_id, username)