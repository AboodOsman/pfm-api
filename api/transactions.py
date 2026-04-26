# api/transactions.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.utils import jsonable
from repositories.transaction_repository import (
    
    get_transactions_by_user,
    delete_transaction,
)
from services.transaction_service import add_transaction_flow
router = APIRouter(prefix="/transactions", tags=["Transactions"])


class TransactionCreate(BaseModel):
    user_id: int
    category_id: int | None=None
    amount: float
    txn_date: str  # YYYY-MM-DD
    txn_type: str  # INCOME / EXPENSE
    note: str | None = None


@router.post("/")
def api_create_transaction(body: TransactionCreate):
    try:
        result = add_transaction_flow(
            user_id=body.user_id,
            amount=body.amount,
            txn_date=body.txn_date,
            txn_type=body.txn_type,
            note=body.note or "",
            category_id=body.category_id,  # can be None
        )
        return jsonable(result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        return jsonable(t)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/user/{user_id}")
def api_get_transactions_for_user(user_id: int):
    return jsonable(get_transactions_by_user(user_id))


@router.delete("/{transaction_id}")
def api_delete_transaction(transaction_id: str):
    delete_transaction(transaction_id)
    return {"ok": True}