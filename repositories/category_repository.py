# repositories/category_repository.py

from typing import List, Dict, Optional
from google.cloud import firestore

from db.firebase import get_db
from services.cache import categories_cache, invalidate_categories

CATEGORIES_COL = "categories"
COUNTERS_COL = "counters"
CATEGORY_COUNTER_DOC = "categories"


def _db():
    return get_db()


def _validate_name(name: str) -> str:
    if not name or not str(name).strip():
        raise ValueError("Category name is required")
    return str(name).strip()


def _validate_category_id(category_id: int) -> int:
    if not isinstance(category_id, int) or category_id <= 0:
        raise ValueError("category_id must be a positive integer")
    return category_id


def _get_next_category_id() -> int:
    """
    Auto-increment category_id using a counter document:
      counters/categories  { next_id: 1 }
    """
    db = _db()
    counter_ref = db.collection(COUNTERS_COL).document(CATEGORY_COUNTER_DOC)

    @firestore.transactional
    def txn_increment(transaction: firestore.Transaction) -> int:
        snap = counter_ref.get(transaction=transaction)
        if not snap.exists:
            # first time
            next_id = 1
            transaction.set(counter_ref, {"next_id": 2})
            return next_id

        data = snap.to_dict() or {}
        next_id = int(data.get("next_id", 1))
        transaction.update(counter_ref, {"next_id": next_id + 1})
        return next_id

    transaction = db.transaction()
    return txn_increment(transaction)


def create_category(name: str) -> Dict:
    """
    Creates a category with auto-increment integer category_id.
    Document id will be the same as category_id (string).
    """
    name = _validate_name(name)
    db = _db()

    new_id = _get_next_category_id()
    doc_ref = db.collection(CATEGORIES_COL).document(str(new_id))

    payload = {
        "category_id": new_id,
        "name": name,
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    doc_ref.set(payload)

    invalidate_categories()

    # Return a clean object (created_at will be server timestamp)
    payload["category_id"] = new_id
    return payload


def get_all_categories() -> List[Dict]:
    """
    Returns all categories ordered by category_id.
    Cached for 1h; invalidated on create/delete.
    """
    cached = categories_cache.get("all")
    if cached is not None:
        return cached

    db = _db()
    qs = db.collection(CATEGORIES_COL).order_by("category_id")
    out: List[Dict] = []
    for doc in qs.stream():
        data = doc.to_dict() or {}
        out.append(data)
    categories_cache["all"] = out
    return out


def get_category_by_id(category_id: int) -> Optional[Dict]:
    category_id = _validate_category_id(category_id)

    # Serve from the cached list when possible.
    cached = categories_cache.get("all")
    if cached is not None:
        for c in cached:
            if int(c.get("category_id", 0)) == category_id:
                return c
        return None

    db = _db()
    doc = db.collection(CATEGORIES_COL).document(str(category_id)).get()
    if not doc.exists:
        return None
    return doc.to_dict()


def delete_category(category_id: int) -> bool:
    category_id = _validate_category_id(category_id)
    db = _db()

    doc_ref = db.collection(CATEGORIES_COL).document(str(category_id))
    doc = doc_ref.get()
    if not doc.exists:
        return False
    doc_ref.delete()
    invalidate_categories()
    return True