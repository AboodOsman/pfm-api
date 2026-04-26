from datetime import datetime, timedelta
from db.firebase import get_db

db = get_db()

db.collection("otp_requests").add({
    "email": "test@example.com",
    "code_hash": "dummyhash",
    "expires_at": datetime.utcnow() + timedelta(minutes=5),
    "attempts": 0,
    "created_at": datetime.utcnow(),
})

print("OTP collection created successfully")