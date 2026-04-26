from repositories.budget_repository import (
    create_budget,
    get_budgets_by_user,
)

USER_ID = 1
CATEGORY_ID = 1      # Food (from your seeded categories)
MONTH = "2026-02-01" # month key

print("=== CREATE BUDGET ===")
b = create_budget(USER_ID, CATEGORY_ID, MONTH, 1000)
print(b)

print("\n=== GET BUDGETS BY USER ===")
print(get_budgets_by_user(USER_ID))