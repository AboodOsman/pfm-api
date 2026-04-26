from repositories.goal_repository import (
    create_goal,
    get_goals_by_user,
    get_active_goals_by_user,
    update_goal_status,
)

USER_ID = 1

print("=== CREATE GOAL ===")
g = create_goal(USER_ID, "Buy a new phone", 3000)
print(g)

print("\n=== GET GOALS BY USER ===")
print(get_goals_by_user(USER_ID))

print("\n=== GET ACTIVE GOALS BY USER ===")
print(get_active_goals_by_user(USER_ID))

print("\n=== UPDATE GOAL STATUS (COMPLETED) ===")
update_goal_status(g["goal_id"], "COMPLETED")
print("Updated. Active goals now:")
print(get_active_goals_by_user(USER_ID))