from repositories.badge_repository import (
    create_badge,
    get_all_badges,
)

print("=== CREATE BADGE ===")
b = create_badge("Saver", "Stayed within budget for a month", 100)
print(b)

print("\n=== GET ALL BADGES ===")
print(get_all_badges())