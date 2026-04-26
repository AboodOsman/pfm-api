# api/badges.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.utils import jsonable
from repositories.badge_repository import create_badge, get_all_badges

router = APIRouter(prefix="/badges", tags=["Badges"])


class BadgeCreate(BaseModel):
    name: str
    description: str
    points: int


@router.get("/")
def api_list_badges():
    return jsonable(get_all_badges())


@router.post("/")
def api_create_badge(body: BadgeCreate):
    try:
        b = create_badge(body.name, body.description, body.points)
        return jsonable(b)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))