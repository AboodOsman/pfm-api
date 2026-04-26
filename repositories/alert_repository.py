# repositories/alert_repository.py

from datetime import datetime
from db.firebase import get_db

COL = "alerts"


def _col():
    return get_db().collection(COL)


def create_alert(user_id: int, alert_type: str, message: str, txn_id: str | None = None):
    data = {
        "user_id": int(user_id),
        "alert_type": alert_type,
        "message": message,
        "transaction_id": txn_id,
        "is_read": False,
        "created_at": datetime.utcnow(),
    }

    doc_ref = _col().document()
    doc_ref.set(data)
    return {"alert_id": doc_ref.id, **data}


def get_alerts_by_user(user_id: int):
    qs = _col().where("user_id", "==", int(user_id))
    return [{"alert_id": d.id, **d.to_dict()} for d in qs.stream()]