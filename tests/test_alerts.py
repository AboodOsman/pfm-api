from repositories.alert_repository import (
    create_alert,
    get_alerts_by_user,
)

USER_ID = 1

print("=== CREATE ALERT ===")
a = create_alert(
    user_id=USER_ID,
    alert_type="BUDGET_NEAR_LIMIT",
    message="You are close to your Food budget for this month.",
    txn_id=None
)
print(a)

print("\n=== GET ALERTS BY USER ===")
print(get_alerts_by_user(USER_ID))