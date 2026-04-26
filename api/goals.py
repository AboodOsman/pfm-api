from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.utils import jsonable
from repositories.goal_repository import (
    create_goal,
    get_goals_by_user,
    get_active_goals_by_user,
    update_goal_status,
    get_goal_by_id,   # make sure this exists in goal_repository.py
)
from repositories.user_repository import add_points_to_user

router = APIRouter(prefix="/goals", tags=["Goals"])

GOAL_CREATE_POINTS = 10
GOAL_COMPLETE_POINTS = 25


class GoalCreate(BaseModel):
    user_id: int
    name: str
    target_amt: float


class GoalStatusUpdate(BaseModel):
    status: str  # "ACTIVE" / "PAUSED" / "COMPLETED" / "CANCELLED"


@router.post("/")
def api_create_goal(body: GoalCreate):
    try:
        g = create_goal(body.user_id, body.name, body.target_amt)

        # give points when user creates a goal
        add_points_to_user(body.user_id, GOAL_CREATE_POINTS)

        g["points_earned"] = GOAL_CREATE_POINTS
        return jsonable(g)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/user/{user_id}")
def api_get_goals_user(user_id: int):
    return jsonable(get_goals_by_user(user_id))


@router.get("/user/{user_id}/active")
def api_get_active_goals_user(user_id: int):
    return jsonable(get_active_goals_by_user(user_id))


@router.put("/{goal_id}/status")
def api_update_goal_status(goal_id: str, body: GoalStatusUpdate):
    try:
        goal = get_goal_by_id(goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")

        # update goal status
        ok = update_goal_status(goal_id, body.status)

        points_earned = 0

        # give points only when completed for the first time
        old_status = str(goal.get("status", "")).upper()
        new_status = body.status.upper()

        if old_status != "COMPLETED" and new_status == "COMPLETED":
            add_points_to_user(goal["user_id"], GOAL_COMPLETE_POINTS)
            points_earned = GOAL_COMPLETE_POINTS

        return {
            "ok": bool(ok),
            "points_earned": points_earned
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))