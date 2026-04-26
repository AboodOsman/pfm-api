# api/categories.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.utils import jsonable
from repositories.category_repository import (
    create_category,
    get_all_categories,
    get_category_by_id,
    delete_category,
)

router = APIRouter(prefix="/categories", tags=["Categories"])


class CategoryCreate(BaseModel):
    name: str


@router.post("/")
def api_create_category(body: CategoryCreate):
    try:
        c = create_category(body.name)
        return jsonable(c)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
def api_get_all_categories():
    return jsonable(get_all_categories())


@router.get("/{category_id}")
def api_get_category(category_id: int):
    c = get_category_by_id(category_id)
    if not c:
        raise HTTPException(status_code=404, detail="Category not found")
    return jsonable(c)


@router.delete("/{category_id}")
def api_delete_category(category_id: int):
    ok = delete_category(category_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"ok": True}