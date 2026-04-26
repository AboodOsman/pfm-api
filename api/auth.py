# api/auth.py

import os
import random
import hashlib
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from google.cloud.firestore_v1 import Query

from db.firebase import get_db
from repositories.user_repository import get_user_by_id, create_user, update_user

router = APIRouter(prefix="/auth", tags=["Auth"])
OTP_COL = "otp_requests"


# -------------------------
# Models
# -------------------------
class RequestOTP(BaseModel):
    email: EmailStr


class VerifyOTP(BaseModel):
    email: EmailStr
    otp: str
    name: str
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# -------------------------
# Helpers
# -------------------------
def _hash(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _stable_user_id(email: str) -> int:
    """
    Stable user_id from email (same every run).
    We take first 8 bytes of sha256 and convert to int.
    """
    digest = hashlib.sha256(email.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % 2000000000  # keep it in int range


def _send_otp_email(to_email: str, code: str) -> None:
    gmail_user = os.getenv("GMAIL_USER")
    gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_user or not gmail_app_password:
        raise HTTPException(
            status_code=500,
            detail="GMAIL_USER / GMAIL_APP_PASSWORD not set in environment variables",
        )

    subject = "Your PFM OTP Code"
    body = f"Your OTP code is: {code}\n\nThis code expires in 5 minutes."

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(gmail_user, gmail_app_password)
            server.sendmail(gmail_user, [to_email], msg.as_string())
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(
            status_code=500,
            detail="Gmail authentication failed. Make sure you used an App Password (not your normal password).",
        )
    except (TimeoutError, smtplib.SMTPServerDisconnected) as e:
        raise HTTPException(
            status_code=504,
            detail=f"Email server timed out: {str(e)}. Please retry.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


# -------------------------
# Routes
# -------------------------
@router.post("/request-otp")
def request_otp(body: RequestOTP):
    db = get_db()
    email = body.email.lower().strip()

    code = f"{random.randint(0, 999999):06d}"
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=5)

    # Save OTP request in Firestore
    db.collection(OTP_COL).add(
        {
            "email": email,
            "code_hash": _hash(code),
            "expires_at": expires_at,
            "attempts": 0,
            "created_at": now,  # ✅ was now() (wrong)
        }
    )

    # Send OTP via Gmail
    _send_otp_email(email, code)

    return {"ok": True, "message": "OTP sent to email"}


@router.post("/verify-otp")
def verify_otp(body: VerifyOTP):
    db = get_db()
    email = body.email.lower().strip()

    qs = (
        db.collection(OTP_COL)
        .where("email", "==", email)
        .order_by("created_at", direction=Query.DESCENDING)
        .limit(1)
    )

    docs = list(qs.stream())
    if not docs:
        raise HTTPException(status_code=400, detail="No OTP request found")

    doc = docs[0]
    data = doc.to_dict() or {}

    expires_at = data.get("expires_at")
    if not expires_at:
        raise HTTPException(status_code=400, detail="OTP record is invalid (missing expires_at)")

    # ✅ timezone-safe compare
    now = datetime.now(timezone.utc)
    if getattr(expires_at, "tzinfo", None) is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if now > expires_at:
        doc.reference.delete()
        raise HTTPException(status_code=400, detail="OTP expired")

    attempts = int(data.get("attempts", 0))
    if attempts >= 5:
        raise HTTPException(status_code=400, detail="Too many attempts")

    if _hash(body.otp.strip()) != data.get("code_hash"):
        doc.reference.update({"attempts": attempts + 1})
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # OTP is correct => delete OTP so it can't be reused
    doc.reference.delete()

    # Create or update user (stable ID)
    user_id = _stable_user_id(email)
    user = get_user_by_id(user_id)

    if not user:
     user = create_user(
        user_id,
        body.name.strip(),
        email,
        body.password.strip(),
    )
    else:
     user = update_user(
        user_id,
        name=body.name.strip(),
        email=email,
        password=body.password,
    )

    return {"ok": True, "user": user} 

@router.post("/login")
def login(body: LoginRequest):
    db = get_db()
    email = body.email.lower().strip()
    password = body.password.strip()

    qs = db.collection("users").where("email", "==", email).limit(1).stream()
    docs = list(qs)

    if not docs:
        raise HTTPException(status_code=404, detail="Email not found")

    user = docs[0].to_dict() or {}

    saved_password = str(user.get("password", "")).strip()

    if saved_password != password:
        raise HTTPException(status_code=401, detail="Wrong password")

    return user