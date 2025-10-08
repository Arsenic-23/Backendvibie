from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import init_db
from routers import users, stream, queue, search, suggest, audio  # Added audio router
from ws.websocket import router as websocket_router

# Create FastAPI app first
app = FastAPI(title="Vibie Backend 🎧")

# CORS
origins = ["*", "http://localhost:3000", "https://vibie.vercel.app"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Init DB
init_db()

# Register routers
app.include_router(suggest.router)
app.include_router(search.router)
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(stream.router, prefix="/stream", tags=["Stream"])
app.include_router(queue.router, prefix="/queue", tags=["Queue"])
app.include_router(audio.router, prefix="/audio", tags=["Audio"])  # ✅ Added audio endpoint
app.include_router(websocket_router)

# Health check route
@app.get("/")
def root():
    return {"message": "Vibie Backend is Live 🎧"}
