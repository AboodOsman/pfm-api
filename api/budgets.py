# api/budgets.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.utils import jsonable
from repositories.budget_repository import create_budget, get_budgets_by_user

router = APIRouter(prefix="/budgets", tags=["Budgets"])


class BudgetCreate(BaseModel):
    user_id: int
    category_id: int
    month: str        # "YYYY-MM-01"
    limit: float


@router.post("/")
def api_create_budget(body: BudgetCreate):
    try:
        b = create_budget(body.user_id, body.category_id, body.month, body.limit)
        return jsonable(b)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/user/{user_id}")
def api_get_budgets_for_user(user_id: int):
    return jsonable(get_budgets_by_user(user_id))