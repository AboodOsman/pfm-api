# services/badge_service.py

from typing import Dict, Any, List, Optional

from repositories import badge_repository as badge_repo
from repositories import transaction_repository as txn_repo
from repositories import goal_repository as goal_repo
from repositories import budget_repository as budget_repo
from repositories import alert_repository as alert_repo


DEFAULT_BADGES = [
    {"name": "Starter", "description": "Created your first transaction", "points": 10},
    {"name": "Tracker", "description": "Added 10 transactions", "points": 25},
    {"name": "Habit Builder", "description": "Added 30 transactions", "points": 50},
    {"name": "Goal Setter", "description": "Created your first goal", "points": 15},
    {"name": "Focused", "description": "Has an ACTIVE goal", "points": 20},
    {"name": "Budgeter", "description": "Created at least one budget", "points": 20},
    {"name": "Inbox Zero", "description": "Has zero unread alerts", "points": 15},
    {"name": "Big Spender", "description": "Total transaction amount >= 1000", "points": 30},
]


def ensure_default_badges_exist() -> List[Dict[str, Any]]:
    """
    Make sure default badges exist in Firestore.
    """
    existing = badge_repo.get_all_badges() or []
    existing_names = {(b.get("name") or "").strip().lower() for b in existing}

    for b in DEFAULT_BADGES:
        if b["name"].strip().lower() not in existing_names:
            badge_repo.create_badge(b["name"], b["description"], b["points"])

    return badge_repo.get_all_badges() or []


def calculate_badges_for_user(user_id: int) -> Dict[str, Any]:
    """
    Computes which badges are earned for the user.
    NOTE: this does NOT "store" earned badges yet.
    It only calculates.
    """
    all_badges = ensure_default_badges_exist()

    txns = txn_repo.get_transactions_by_user(user_id) or []
    txn_count = len(txns)

    total_amount = 0.0
    for t in txns:
        # your txn tuple: (id, user_id, category_id, amount, date)
        try:
            total_amount += float(t[3])
        except Exception:
            pass

    goals = goal_repo.get_goals_by_user(user_id) or []
    goals_count = len(goals)

    active_goals = goal_repo.get_active_goals_by_user(user_id) or []
    active_goals_count = len(active_goals)

    budgets = budget_repo.get_budgets_by_user(user_id) or []
    budgets_count = len(budgets)

    alerts = alert_repo.get_alerts_by_user(user_id) or []
    unread_count = sum(1 for a in alerts if a.get("is_read") is False)

    def is_earned(name: str) -> bool:
        n = name.strip().lower()
        if n == "starter":
            return txn_count >= 1
        if n == "tracker":
            return txn_count >= 10
        if n == "habit builder":
            return txn_count >= 30
        if n == "goal setter":
            return goals_count >= 1
        if n == "focused":
            return active_goals_count >= 1
        if n == "budgeter":
            return budgets_count >= 1
        if n == "inbox zero":
            return unread_count == 0
        if n == "big spender":
            return total_amount >= 1000
        return False

    earned = []
    not_earned = []

    for b in all_badges:
        b2 = dict(b)
        b2["earned"] = is_earned(b.get("name", ""))
        if b2["earned"]:
            earned.append(b2)
        else:
            not_earned.append(b2)

    return {
        "user_id": user_id,
        "earned": earned,
        "not_earned": not_earned,
        "summary": {
            "txn_count": txn_count,
            "total_amount": round(total_amount, 2),
            "goals_count": goals_count,
            "active_goals_count": active_goals_count,
            "budgets_count": budgets_count,
            "unread_alerts": unread_count,
        },
    }