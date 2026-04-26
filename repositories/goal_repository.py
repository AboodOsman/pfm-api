from db.firebase import get_db
from datetime import datetime


def _goals_col():
    return get_db().collection("goals")


def create_goal(user_id: int, name: str, target_amt: float):
    doc_ref = _goals_col().document()
    data = {
        "goal_id": doc_ref.id,
        "user_id": user_id,
        "name": name,
        "target_amt": target_amt,
        "saved_amt": 0,
        "status": "ACTIVE",
        "created_at": datetime.utcnow().isoformat(),
    }
    doc_ref.set(data)
    return data


def get_goal_by_id(goal_id: str):
    doc = _goals_col().document(goal_id).get()
    if not doc.exists:
        return None
    return doc.to_dict()


def get_goals_by_user(user_id: int):
    docs = _goals_col().where("user_id", "==", user_id).stream()
    goals = []
    for doc in docs:
        goals.append(doc.to_dict())
    return goals


def get_active_goals_by_user(user_id: int):
    docs = (
        _goals_col()
        .where("user_id", "==", user_id)
        .where("status", "==", "ACTIVE")
        .stream()
    )
    goals = []
    for doc in docs:
        goals.append(doc.to_dict())
    return goals


def update_goal_status(goal_id: str, status: str):
    doc_ref = _goals_col().document(goal_id)
    doc = doc_ref.get()

    if not doc.exists:
        return False

    doc_ref.update({"status": status})
    return True