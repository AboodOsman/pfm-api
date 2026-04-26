# api/users.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.utils import jsonable
from repositories.user_repository import (
    create_user,
    get_user_by_id,
    get_all_users,
    update_user,
    delete_user,
    get_user_by_email,

)

router = APIRouter(prefix="/users", tags=["Users"])


class UserCreate(BaseModel):
    user_id: int
    name: str
    email: str


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None


@router.post("/")
def api_create_user(body: UserCreate):
    try:
        u = create_user(body.user_id, body.name, body.email)
        return jsonable(u)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/by-email/{email}")
def api_get_user_by_email(email: str):
    u = get_user_by_email(email)
    if not u:
        raise HTTPException(status_code=404, detail="Email not found")
    return jsonable(u)
@router.get("/{user_id}")
def api_get_user(user_id: int):
    u = get_user_by_id(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return jsonable(u)


@router.get("/")
def api_list_users():
    return jsonable(get_all_users())


@router.put("/{user_id}")
def api_update_user(user_id: int, body: UserUpdate):
    try:
        updated = update_user(user_id, name=body.name, email=body.email)
        if not updated:
            raise HTTPException(status_code=404, detail="User not found or no fields to update")
        return jsonable(updated)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{user_id}")
def api_delete_user(user_id: int):
    delete_user(user_id)
    return {"ok": True}