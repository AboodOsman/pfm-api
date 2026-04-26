from repositories.category_repository import create_category, get_all_categories

fixed_categories = [
    "Food",
    "Transport",
    "Rent",
    "Entertainment",
    "Utilities",
    "Education",
    "Health",
    "Shopping",
    "Other"
]

existing = get_all_categories()
existing_names = {c["name"].lower() for c in existing}

for name in fixed_categories:
    if name.lower() in existing_names:
        print("SKIP:", name)
    else:
        created = create_category(name)
        print("CREATED:", created)

print("✅ Categories initialized")