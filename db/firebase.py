import json
import os
import firebase_admin
from firebase_admin import credentials, firestore

_db = None


def _build_credential() -> credentials.Certificate:
    """
    Resolve Firebase Admin credentials from one of:

      1) FIREBASE_KEY_JSON  — full service-account JSON pasted as an env var.
         Use this on hosts like Render/Heroku/Fly that don't have a writable
         filesystem for secret files.

      2) FIREBASE_KEY_PATH  — absolute path to a service-account JSON file on
         disk. Use this in local development.

    Whichever is present wins; FIREBASE_KEY_JSON is checked first because on
    cloud hosts it's the more reliable option.
    """
    key_json = os.environ.get("FIREBASE_KEY_JSON")
    if key_json and key_json.strip():
        try:
            data = json.loads(key_json)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"FIREBASE_KEY_JSON is set but is not valid JSON: {e}"
            )
        return credentials.Certificate(data)

    key_path = os.environ.get("FIREBASE_KEY_PATH")
    if key_path and key_path.strip():
        return credentials.Certificate(key_path)

    raise RuntimeError(
        "Firebase credentials missing: set FIREBASE_KEY_JSON (full JSON content) "
        "or FIREBASE_KEY_PATH (path to a service-account JSON file)."
    )


def get_db():
    global _db
    if _db is not None:
        return _db

    if not firebase_admin._apps:
        firebase_admin.initialize_app(_build_credential())

    _db = firestore.client()
    return _db
