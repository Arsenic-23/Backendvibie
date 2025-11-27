from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import init_db

# NEW robust routers
from routers.stream import router as stream_router
from routers.queue import router as queue_router
from ws.websocket import router as websocket_router

# Keep your existing search, suggest, audio (these are fine)
from routers import search, suggest, audio

app = FastAPI(title="Vibie Backend 🎧")

# CORS settings (update for production later)
origins = [
    "*",
    "http://localhost:3000",
    "https://vibie.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB
init_db()

# Register routers (ONLY the new ones)
app.include_router(suggest.router)
app.include_router(search.router)
app.include_router(audio.router, prefix="/audio", tags=["Audio"])

# NEW stream system
app.include_router(stream_router, prefix="/stream", tags=["Stream"])
app.include_router(queue_router, prefix="/queue", tags=["Queue"])
app.include_router(websocket_router)

# Root
@app.get("/")
def root():
    return {"message": "Vibie Backend is Live 🎧 (New Stream System Active)"}