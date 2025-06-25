from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import init_db
from routers import users, stream, queue, websockets  # ✅ fix here

app = FastAPI(title="Vibie Backend 🎧")

origins = [
    "*",
    "http://localhost:3000",
    "https://t.me/vibie_bot",
    "https://vibie.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(stream.router, prefix="/stream", tags=["Stream"])
app.include_router(queue.router, prefix="/queue", tags=["Queue"])
app.include_router(websockets.router)  # ✅ fix here too

@app.get("/")
def root():
    return {"message": "Vibie Backend is Live 🎧"}