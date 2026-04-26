# services/budget_service.py

from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from repositories.budget_repository import get_budgets_by_user
from repositories.transaction_repository import get_transactions_by_user
from repositories.alert_repository import create_alert


def _month_key(dt: datetime) -> str:
    return f"{dt.year:04d}-{dt.month:02d}-01"


def _find_budget_limit(user_id: int, category_id: int, month: str) -> Optional[float]:
    budgets = get_budgets_by_user(user_id) or []
    for b in budgets:
        if int(b.get("category_id", 0)) == int(category_id) and str(b.get("month")) == month:
            return float(b.get("monthly_limit", 0))
    return None


def _parse_txn_row(row: Tuple):
    """
    Supports both formats:
      5 fields: (tid, uid, cid, amount, txn_dt)
      6 fields: (tid, uid, cid, amount, txn_type, txn_dt)
    Returns: (tid, uid, cid, amount, txn_type, txn_dt)
    If txn_type missing -> assumes EXPENSE for safety in budget checks.
    """
    if len(row) == 5:
        tid, uid, cid, amount, txn_dt = row
        txn_type = "EXPENSE"  # default assumption if missing
        return tid, uid, cid, amount, txn_type, txn_dt

    if len(row) == 6:
        tid, uid, cid, amount, txn_type, txn_dt = row
        return tid, uid, cid, amount, txn_type, txn_dt

    raise ValueError(f"Unexpected transaction row format: {row}")


def _sum_expenses_for_category_month(rows: List[Tuple], category_id: int, month: str) -> float:
    total = 0.0
    for r in rows:
        _tid, _uid, cid, amount, txn_type, txn_dt = _parse_txn_row(r)

        if int(cid) != int(category_id):
            continue
        if not txn_dt:
            continue
        if _month_key(txn_dt) != month:
            continue
        if str(txn_type).upper() != "EXPENSE":
            continue

        total += float(amount)
    return total


def check_budget_and_alert(user_id: int, category_id: int, txn_dt: datetime) -> Optional[Dict[str, Any]]:
    """
    Returns created alert dict or None.
    """
    month = _month_key(txn_dt)
    limit_amt = _find_budget_limit(user_id, category_id, month)

    if limit_amt is None:
        return None

    rows = get_transactions_by_user(user_id) or []
    spent = _sum_expenses_for_category_month(rows, category_id, month)

    if spent > limit_amt:
        msg = (
            f"Budget exceeded for category {category_id} in {month}. "
            f"Limit={limit_amt:.2f}, Spent={spent:.2f}"
        )
        return create_alert(user_id=user_id, alert_type="BUDGET_EXCEEDED", message=msg)

    return None