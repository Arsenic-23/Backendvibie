from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import init_db

# Ensure Firebase Admin + Firestore initialized
from utils.firebase import get_firestore  # noqa: F401

# NEW robust stream system routers
from routers.stream import router as stream_router
from routers.queue import router as queue_router
from ws.websocket import router as websocket_router

# Existing independent routers
from routers import search, suggest, audio, analytics


app = FastAPI(title="Vibie Backend 🎧")

# CORS
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

# Init DB
init_db()


# --------------------------
# Router Registration
# --------------------------

# General utilities
app.include_router(suggest.router)
app.include_router(search.router)
app.include_router(audio.router, prefix="/audio", tags=["Audio"])

# Stream ecosystem
app.include_router(stream_router, prefix="/stream", tags=["Stream"])
app.include_router(queue_router, prefix="/queue", tags=["Queue"])
app.include_router(websocket_router)

# Analytics (router already has prefix="/analytics")
app.include_router(analytics.router)


# Root
@app.get("/")
def root():
    return {
        "message": "Vibie Backend is Live 🎧",
        "stream_system": "Active",
        "analytics": "Active",
        "firebase": "Active",
        "firestore": "Active",
    }
