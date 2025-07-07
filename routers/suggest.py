from fastapi import APIRouter, Query
from typing import List
from youtubesearchpython import Suggestions

router = APIRouter(prefix="/suggest", tags=["Suggestions"])

@router.get("/")
def suggest(q: str = Query(...)) -> dict:
    try:
        suggestion_result = Suggestions(q).get()
        suggestions = suggestion_result.get("suggestions", [])
        return {"results": suggestions[:10]}
    except Exception as e:
        return {"results": [], "error": str(e)}