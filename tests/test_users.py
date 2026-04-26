from repositories.user_repository import (
    create_user,
    get_user_by_id,
    list_all_users,
    update_user,
    delete_user,
)

USER_ID = 1

print("=== CREATE USER ===")
print(create_user(USER_ID, "Test User", "test@email.com"))

print("\n=== GET USER ===")
print(get_user_by_id(USER_ID))

print("\n=== UPDATE USER ===")
print(update_user(USER_ID, name="Updated Name"))

print("\n=== LIST USERS ===")
print(list_all_users())

print("\n=== DELETE USER ===")
print(delete_user(USER_ID))