from fastapi import APIRouter, Query
from youtubesearchpython import VideosSearch

router = APIRouter(prefix="/search", tags=["Search"])

@router.get("/")
def search_youtube(q: str = Query(..., description="Search query")):
    try:
        # Perform YouTube search for the query, always return 10 results
        videos_search = VideosSearch(q, limit=30)
        results = videos_search.result().get("result", [])

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

        return {"results": parsed_results}

    except Exception as e:
        return {"error": str(e)}