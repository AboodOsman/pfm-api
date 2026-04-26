from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from services.ai_chat_service import generate_finance_reply

router = APIRouter(prefix="/ai", tags=["AI"])


class AiChatRequest(BaseModel):
    user_id: str
    question: str
    totals: dict[str, Any] = {}
    transactions: list[dict[str, Any]] = []
    goals: list[dict[str, Any]] = []


@router.post("/chat")
def ai_chat(body: AiChatRequest):
    try:
        answer = generate_finance_reply(
            user_id=body.user_id,
            question=body.question,
            totals=body.totals,
            transactions=body.transactions,
            goals=body.goals,
        )
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))