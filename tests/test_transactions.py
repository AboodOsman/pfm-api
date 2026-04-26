from repositories.transaction_repository import (
    create_transaction,
    get_transactions_by_user,
    delete_transaction,
)

USER_ID = 1

print("=== CREATE TRANSACTION ===")
t = create_transaction(USER_ID, 1, 25.5, "2026-02-01", "EXPENSE", "Firebase test")
print(t)

print("\n=== LIST TRANSACTIONS FOR USER ===")
rows = get_transactions_by_user(USER_ID)
print(rows)

print("\n=== DELETE THE CREATED TRANSACTION ===")
print(delete_transaction(t["transaction_id"]))