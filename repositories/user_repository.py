from db.firebase import get_db
from services.cache import (
    user_by_id_cache,
    user_by_email_cache,
    invalidate_user,
)

# -------------------------
# Helpers
# -------------------------

def _users_col():
    return get_db().collection("users")


# -------------------------
# Repository functions
# -------------------------

def create_user(user_id: int, name: str, email: str, password: str):
    doc_ref = _users_col().document(str(user_id))
    data = {
        "user_id": user_id,
        "name": name,
        "email": email,
        "password": password,
        "points": 0,
    }
    doc_ref.set(data)
    invalidate_user(user_id=user_id, email=email)
    return data


def get_user_by_id(user_id: int):
    """Cached for 60s. Invalidated on update/delete/create."""
    key = int(user_id)
    cached = user_by_id_cache.get(key)
    if cached is not None:
        return cached

    doc = _users_col().document(str(user_id)).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    user_by_id_cache[key] = data
    return data


def get_all_users():
    """
    Return all users.
    Not cached — list endpoint is rarely hit and changes mid-flight.
    """
    users = []
    for doc in _users_col().stream():
        users.append(doc.to_dict())
    return users


def update_user(user_id: int, name: str = None, email: str = None, password: str = None):
    updates = {}

    if name is not None:
        updates["name"] = name
    if email is not None:
        updates["email"] = email
    if password is not None:
        updates["password"] = password

    if not updates:
        return None

    doc_ref = _users_col().document(str(user_id))
    doc_ref.update(updates)

    # Invalidate both old and new email keys (if email changed)
    invalidate_user(user_id=user_id, email=email)

    return get_user_by_id(user_id)


def delete_user(user_id: int):
    # Read first so we can drop the email key from cache too
    existing = get_user_by_id(user_id)
    _users_col().document(str(user_id)).delete()
    invalidate_user(
        user_id=user_id,
        email=(existing or {}).get("email"),
    )
    return True


def get_user_by_email(email: str):
    """Cached for 60s. Invalidated on update/create/delete."""
    email = email.lower().strip()
    cached = user_by_email_cache.get(email)
    if cached is not None:
        return cached

    qs = _users_col().where("email", "==", email).limit(1).stream()
    docs = list(qs)
    if not docs:
        return None

    data = docs[0].to_dict()
    user_by_email_cache[email] = data
    # Also warm the by-id cache while we're here
    uid = data.get("user_id")
    if uid is not None:
        try:
            user_by_id_cache[int(uid)] = data
        except (TypeError, ValueError):
            pass
    return data


def add_points_to_user(user_id: int, points: int):
    doc_ref = _users_col().document(str(user_id))
    doc = doc_ref.get()

    if not doc.exists:
        raise Exception("User not found")

    user = doc.to_dict()

    # if old user has no points yet → start from 0
    current_points = int(user.get("points", 0))
    new_points = current_points + int(points)

    doc_ref.update({"points": new_points})

    user["points"] = new_points
    invalidate_user(user_id=user_id, email=user.get("email"))
    return user