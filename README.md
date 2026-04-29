# Vibie Backend 🎧

The official backend service for **Vibie**, a real-time collaborative music streaming application. Built with **FastAPI**, it handles real-time stream state management, audio extraction, queue synchronization, and WebSockets to create a seamless live listening experience.

## ✨ Features

- **Real-time Ecosystem:** WebSocket-powered live rooms for synchronized music playback across multiple clients.
- **Audio Streaming Extraction:** Direct integration with `yt-dlp` to fetch and stream high-quality audio formats on the fly.
- **Collaborative Queues:** Robust streaming queues allowing users to add, play, and skip tracks interactively.
- **Firebase Auth & Firestore:** Integrated with Firebase Admin for secure JWT token verification and syncing basic user presence.
- **SQLModel & PostgreSQL:** Type-safe database interactions mapping seamlessly between Python objects and the relational database.
- **YouTube Search & Suggest:** Native endpoints to search for tracks and retrieve autocomplete suggestions.

## 💻 Tech Stack

- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Python)
- **ASGI Server:** Uvicorn
- **Database ORM:** SQLModel / SQLAlchemy
- **Database Engine:** PostgreSQL (`psycopg2-binary`)
- **Authentication:** Firebase Admin SDK
- **Media Extraction:** `yt-dlp` & `youtube-search-python`
- **Deployment Ready:** Configured with `Render.yaml` and `Procfile`.

## 📂 Project Structure

```text
Backendvibie-main-2/
├── db/               # Database initialization and SQLModel schemas
├── routers/          # API Route handlers (Stream, Queue, Audio, Search, Analytics)
├── utils/            # Helper utilities (Auth, Firebase, Notifications, Memory)
├── ws/               # WebSocket connection managers and event handlers
├── main.py           # FastAPI application entry point and router registration
├── requirements.txt  # Python dependencies
├── Procfile          # Heroku-style process file
├── render.yaml       # Render cloud deployment configuration
└── .env              # Environment variables (Ignored in VCS)
```

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL database
- Firebase Service Account Key (`firebase_credentials.json`)
- (Optional) `cookies.txt` for authenticated YouTube/yt-dlp extraction to avoid rate limits.

### 1. Clone the repository

```bash
git clone https://github.com/your-username/Backendvibie.git
cd Backendvibie
```

### 2. Set up a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configuration

1. Create a `.env` file in the root directory and configure your PostgreSQL URL:
   ```env
   DATABASE_URL=postgresql://username:password@localhost/vibie_db
   ```
2. Place your `firebase_credentials.json` in the root directory. Ensure the file contains your valid Firebase Admin service account keys.
3. If using `yt-dlp` with cookies (to bypass age restrictions or bot blocks), place a valid `cookies.txt` in the root directory.

### 5. Run the Server

Start the FastAPI application using Uvicorn:

```bash
uvicorn main:app --reload
```

The API will be accessible at:
- **Health Check:** `http://localhost:8000/`
- **Interactive API Docs (Swagger UI):** `http://localhost:8000/docs`
- **Alternative API Docs (ReDoc):** `http://localhost:8000/redoc`

## 📡 Core API Routes

- **`GET /audio/fetch`**: Extracts the best audio stream URL for a given YouTube Video ID.
- **`POST /stream/create`**: Creates a new live music stream/room.
- **`POST /stream/join`**: Joins an active stream.
- **`POST /stream/queue/next`**: Plays the next song in the stream queue and broadcasts the player state.
- **`WS /ws/...`**: Upgrades connection to WebSocket for real-time room events.

## 🚀 Deployment

The project contains a `render.yaml` for seamless deployment on [Render](https://render.com/). Make sure to add the required environment variables (`DATABASE_URL`) and upload your `firebase_credentials.json` securely via Render Secret Files.

## 📄 License

This project is licensed under the MIT License.
