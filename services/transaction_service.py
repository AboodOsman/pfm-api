# services/transaction_service.py

from typing import Optional, Dict, Any

from repositories.transaction_repository import create_transaction
from services.categorization_service import categorize_transaction
from services.budget_service import check_budget_and_alert
from services.goal_service import evaluate_goals_after_transaction


def add_transaction_flow(
    user_id: int,
    amount: float,
    txn_date: str,
    txn_type: str,
    note: str = "",
    category_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Full flow:
    1) Auto-categorize if category_id not provided
    2) Save transaction


    
    3) If EXPENSE -> budget check -> alert
    4) Goals check -> badges + alert
    """
    txn_type = (txn_type or "").strip().upper()
    if txn_type not in ("INCOME", "EXPENSE"):
        raise ValueError("txn_type must be INCOME or EXPENSE")

    # 1) Categorize if needed
    categorization = {"auto": False, "source": None, "confidence": None, "category_name": None}

    if category_id is None:
        cat = categorize_transaction(note or "")
        category_id = cat["category_id"]
        categorization = {
            "auto": True,
            "source": cat.get("source"),
            "confidence": cat.get("confidence"),
            "category_name": cat.get("category_name"),
        }

    # 2) Create transaction
    txn = create_transaction(
        user_id=user_id,
        category_id=int(category_id),
        amount=amount,
        txn_date=txn_date,
        txn_type=txn_type,
        note=note or "",
        auto_categorized=(categorization["auto"] and categorization["source"] == "ai"),
        ai_confidence=categorization.get("confidence"),
    )

    # 3) Budget check only for expenses
    budget_alert = None
    if txn_type == "EXPENSE":
        budget_alert = check_budget_and_alert(
            user_id=user_id,
            category_id=int(category_id),
            txn_dt=txn["transaction_date"],
        )

    # 4) Goals + badges
    goals_result = evaluate_goals_after_transaction(user_id)

    return {
        "transaction": txn,
        "categorization": categorization,
        "budget_alert": budget_alert,
        "goals_result": goals_result,
    }