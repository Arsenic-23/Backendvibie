# main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import init_db
from routers import users, stream, queue
from ws.websocket import websocket_router

app = FastAPI(title="Vibie Backend")

# ✅ CORS for Mini App (update your frontend domain here)
origins = [
    "https://t.me/vibie_bot/Vibiebot",  # replace with your actual Mini App URL
    "http://localhost:3000",            # for local testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_db()

# Include routers
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(stream.router, prefix="/stream", tags=["Stream"])
app.include_router(queue.router, prefix="/queue", tags=["Queue"])
app.include_router(websocket_router)

@app.get("/")
def root():
    return {"message": "Vibie Backend is Live 🎧"}
