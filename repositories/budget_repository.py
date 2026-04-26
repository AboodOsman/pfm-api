# repositories/budget_repository.py

from datetime import datetime
from db.firebase import get_db

COL = "budgets"


def _col():
    return get_db().collection(COL)


def create_budget(user_id: int, category_id: int, month: str, limit: float):
    data = {
        "user_id": int(user_id),
        "category_id": int(category_id),
        "month": month,  # "YYYY-MM-01"
        "monthly_limit": float(limit),
        "created_at": datetime.utcnow(),
    }

    doc_ref = _col().document()
    doc_ref.set(data)
    return {"budget_id": doc_ref.id, **data}


def get_budgets_by_user(user_id: int):
    qs = _col().where("user_id", "==", int(user_id))
    return [{"budget_id": d.id, **d.to_dict()} for d in qs.stream()]