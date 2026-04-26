from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.utils import jsonable
from repositories.alert_repository import create_alert, get_alerts_by_user

router = APIRouter(prefix="/alerts", tags=["Alerts"])


class AlertCreate(BaseModel):
    user_id: int
    alert_type: str
    message: str
    txn_id: str | None = None


@router.post("/")
def api_create_alert(body: AlertCreate):
    try:
        a = create_alert(
            user_id=body.user_id,
            alert_type=body.alert_type,
            message=body.message,
            txn_id=body.txn_id,
        )
        return jsonable(a)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/user/{user_id}")
def api_get_alerts_user(user_id: int):
    return jsonable(get_alerts_by_user(user_id))