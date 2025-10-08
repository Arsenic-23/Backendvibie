from fastapi import APIRouter, HTTPException, Query
import yt_dlp

router = APIRouter(prefix="/audio", tags=["Audio"])

YOUTUBE_URL = "https://www.youtube.com/watch?v="

@router.get("/fetch")
async def fetch_audio_url(video_id: str = Query(..., description="YouTube video ID")):
    try:
        url = f"{YOUTUBE_URL}{video_id}"

        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "format": "bestaudio/best",
            "nocheckcertificate": True,
            "noplaylist": True,
            # Primary method: cookies from browser (best reliability)
            "cookiesfrombrowser": ("chrome",),
        }

        # Optional fallback: use cookies.txt if browser cookies fail
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as browser_err:
            print("Browser cookies failed, trying cookies.txt fallback...")
            ydl_opts.pop("cookiesfrombrowser", None)
            ydl_opts["cookiefile"] = "./cookies.txt"
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

        formats = info.get("formats", [])
        audio_format = next(
            (f for f in formats if f.get("acodec") != "none" and "video" not in f.get("vcodec", "")),
            None
        )

        if not audio_format:
            raise HTTPException(status_code=404, detail="No audio format found")

        return {
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "audioUrl": audio_format.get("url"),
            "source": url
        }

    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=f"Error fetching audio: {str(e)}")
