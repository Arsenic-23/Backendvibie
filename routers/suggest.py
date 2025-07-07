from fastapi import APIRouter, Query
from typing import List
from youtubesearchpython import Suggestions

router = APIRouter(prefix="/suggest", tags=["Suggestions"])

class SuggestionService:
    @staticmethod
    def get(query: str) -> List[str]:
        try:
            suggestions = Suggestions().get(query)
            return suggestions.get("suggestions", [])
        except Exception as e:
            print(f"Suggestion error: {e}")
            return []

@router.get("/")
def get_suggestions(q: str = Query(...)):
    try:
        results = SuggestionService.get(q)
        return {"results": results}
    except Exception as e:
        return {"results": [], "error": str(e)}