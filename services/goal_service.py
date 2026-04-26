# services/goal_service.py

from typing import Dict, Any, List, Tuple

from repositories.goal_repository import get_active_goals_by_user, update_goal_status
from repositories.transaction_repository import get_transactions_by_user
from repositories.badge_repository import create_badge
from repositories.alert_repository import create_alert


def _parse_txn_row(row: Tuple):
    """
    Supports both formats:
      5 fields: (tid, uid, cid, amount, txn_dt)
      6 fields: (tid, uid, cid, amount, txn_type, txn_dt)
    Returns: (tid, uid, cid, amount, txn_type, txn_dt)
    If txn_type missing -> treat as EXPENSE by default (safe).
    """
    if len(row) == 5:
        tid, uid, cid, amount, txn_dt = row
        txn_type = "EXPENSE"
        return tid, uid, cid, amount, txn_type, txn_dt

    if len(row) == 6:
        tid, uid, cid, amount, txn_type, txn_dt = row
        return tid, uid, cid, amount, txn_type, txn_dt

    raise ValueError(f"Unexpected transaction row format: {row}")


def _net_savings(rows: List[Tuple]) -> float:
    income = 0.0
    expense = 0.0

    for r in rows:
        _tid, _uid, _cid, amount, txn_type, _txn_dt = _parse_txn_row(r)
        ttype = str(txn_type).upper()

        if ttype == "INCOME":
            income += float(amount)
        elif ttype == "EXPENSE":
            expense += float(amount)

    return income - expense


def evaluate_goals_after_transaction(user_id: int) -> Dict[str, Any]:
    """
    If net savings >= target_amt => COMPLETE goal + unlock badge + alert
    """
    active_goals = get_active_goals_by_user(user_id) or []
    if not active_goals:
        return {"completed_goals": [], "unlocked_badges": []}

    rows = get_transactions_by_user(user_id) or []
    savings = _net_savings(rows)

    completed = []
    unlocked = []

    for g in active_goals:
        target = float(g.get("target_amt", 0))
        if target <= 0:
            continue

        if savings >= target:
            update_goal_status(g["goal_id"], "COMPLETED")
            completed.append({**g, "status": "COMPLETED"})

            badge = create_badge(
                name=f"Goal Achieved: {g.get('name','')}",
                description=f"Reached net savings target {target:.2f}.",
                points=10,
            )
            unlocked.append(badge)

            create_alert(
                user_id=user_id,
                alert_type="GOAL_COMPLETED",
                message=f"Goal '{g.get('name','')}' completed! Target={target:.2f}",
            )

    return {"completed_goals": completed, "unlocked_badges": unlocked}