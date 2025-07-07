from fastapi import APIRouter, Query
from typing import List

router = APIRouter(prefix="/suggest", tags=["Suggestions"])

class Suggestions:
    @staticmethod
    def get(query: str) -> List[str]:
        # Replace with your actual suggestion logic
        return [f"{query} suggestion 1", f"{query} suggestion 2"]

@router.get("/")
def get_suggestions(q: str = Query(...)):
    try:
        suggestions = Suggestions.get(q)
        return {"results": suggestions}
    except Exception as e:
        return {"results": [], "error": str(e)}