# repositories/transaction_repository.py

from datetime import datetime
from typing import Optional, List, Tuple, Any, Dict
from google.cloud.firestore_v1 import Query

from db.firebase import get_db


TRANSACTIONS_COL = "transactions"


def _col():
    return get_db().collection(TRANSACTIONS_COL)


def create_transaction(
    user_id: int,
    category_id: int,
    amount: float,
    txn_date: str,
    txn_type: str,
    note: str = None,
    *,
    auto_categorized: bool = False,
    ai_confidence: Optional[float] = None,
) -> Dict[str, Any]:
    dt = datetime.strptime(txn_date, "%Y-%m-%d")

    data = {
        "user_id": int(user_id),
        "category_id": int(category_id),
        "amount": float(amount),
        "transaction_date": dt,
        "txn_type": str(txn_type).upper(),          # ✅ stored
        "note": note or "",
        "auto_categorized": bool(auto_categorized),
        "ai_confidence": float(ai_confidence) if ai_confidence is not None else None,
    }

    doc_ref = _col().document()
    doc_ref.set(data)

    return {"transaction_id": doc_ref.id, **data}


def get_transactions_by_user(user_id: int) -> List[Tuple[str, int, int, float, str, Any]]:
    """
    Returns tuples:
      (transaction_id, user_id, category_id, amount, txn_type, transaction_date)
    """
    qs = (
        _col()
        .where("user_id", "==", int(user_id))
        .order_by("transaction_date", direction=Query.DESCENDING)
    )

    out = []
    for doc in qs.stream():
        d = doc.to_dict() or {}
        out.append(
            (
                doc.id,
                int(d.get("user_id", 0)),
                int(d.get("category_id", 0)),
                float(d.get("amount", 0)),
                str(d.get("txn_type", "")).upper(),   # ✅ ADDED
                d.get("transaction_date"),
            )
        )
    return out


def get_transactions_by_user_month(user_id: int, month: str) -> List[Tuple[str, int, int, float, str, Any]]:
    """
    month must be 'YYYY-MM-01'
    Returns tuples:
      (transaction_id, user_id, category_id, amount, txn_type, transaction_date)
    """
    start = datetime.strptime(month, "%Y-%m-%d")

    if start.month == 12:
        end = datetime(start.year + 1, 1, 1)
    else:
        end = datetime(start.year, start.month + 1, 1)

    qs = (
        _col()
        .where("user_id", "==", int(user_id))
        .where("transaction_date", ">=", start)
        .where("transaction_date", "<", end)
        .order_by("transaction_date", direction=Query.DESCENDING)
    )

    out = []
    for doc in qs.stream():
        d = doc.to_dict() or {}
        out.append(
            (
                doc.id,
                int(d.get("user_id", 0)),
                int(d.get("category_id", 0)),
                float(d.get("amount", 0)),
                str(d.get("txn_type", "")).upper(),   # ✅ ADDED
                d.get("transaction_date"),
            )
        )
    return out


def delete_transaction(transaction_id: str) -> bool:
    _col().document(str(transaction_id)).delete()
    return True