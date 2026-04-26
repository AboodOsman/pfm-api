from repositories.category_repository import (
    create_category,
    get_category_by_id,
    list_all_categories,
    update_category,
    delete_category,
)

CAT_ID = 1

print("=== CREATE CATEGORY ===")
print(create_category(CAT_ID, "Food"))

print("\n=== GET CATEGORY ===")
print(get_category_by_id(CAT_ID))

print("\n=== UPDATE CATEGORY ===")
print(update_category(CAT_ID, "Groceries"))

print("\n=== LIST CATEGORIES ===")
print(list_all_categories())

print("\n=== DELETE CATEGORY ===")
print(delete_category(CAT_ID))