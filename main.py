
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import init_db
from routers import users, stream, queue
from ws.websocket import websocket_router

app = FastAPI(title="Vibie Backend 🎧")

# ✅ Allow requests from your frontend (Telegram Mini App + local dev)
origins = [
    "*",  # ← Allow all for now (you can restrict this later to your Vercel URL or Telegram domains)
    "http://localhost:3000",  # local testing
    "https://t.me/vibie_bot",  # Telegram bot link (optional, not used in CORS usually)
    "https://vibie.vercel.app",  # ✅ your actual frontend deployment if hosted on Vercel
]

# ✅ Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        # Allow frontend domains
    allow_credentials=True,
    allow_methods=["*"],          # Allow all HTTP methods: GET, POST, etc.
    allow_headers=["*"],          # Allow all headers
)

# ✅ Initialize the database connection
init_db()

# ✅ Include all routers
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(stream.router, prefix="/stream", tags=["Stream"])
app.include_router(queue.router, prefix="/queue", tags=["Queue"])
app.include_router(websocket_router)

# ✅ Health check route
@app.get("/")
def root():
    return {"message": "Vibie Backend is Live 🎧"}