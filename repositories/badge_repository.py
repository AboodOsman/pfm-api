# repositories/badge_repository.py

from datetime import datetime
from db.firebase import get_db

COL = "badges"


def _col():
    return get_db().collection(COL)


def create_badge(name: str, description: str, points: int):
    data = {
        "name": name,
        "description": description,
        "points": int(points),
        "created_at": datetime.utcnow(),
    }

    doc_ref = _col().document()
    doc_ref.set(data)
    return {"badge_id": doc_ref.id, **data}


def get_all_badges():
    return [{"badge_id": d.id, **d.to_dict()} for d in _col().stream()]