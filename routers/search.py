from fastapi import APIRouter, Query
from typing import Optional
from youtubesearchpython import VideosSearch

router = APIRouter(prefix="/search", tags=["Search"])

@router.get("/")
def search_youtube(q: str = Query(...), limit: int = 10, page_token: Optional[str] = None):
    try:
        # Initial search
        videos_search = VideosSearch(q, limit=limit)
        
        # Use page token if provided
        if page_token:
            videos_search.next()
        
        results = videos_search.result().get("result", [])
        next_token = videos_search.result().get("next", None)

        parsed_results = []
        for item in results:
            parsed_results.append({
                "title": item.get("title"),
                "id": item.get("id"),
                "url": item.get("link"),
                "duration": item.get("duration"),
                "thumbnail": item["thumbnails"][0]["url"] if item.get("thumbnails") else None,
                "channel": item["channel"]["name"] if item.get("channel") else None
            })

        return {
            "results": parsed_results,
            "nextPageToken": next_token  # Send this back to frontend for next fetch
        }

    except Exception as e:
        return {"error": str(e)}