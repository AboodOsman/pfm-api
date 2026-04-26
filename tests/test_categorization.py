from services.categorization_service import categorize_transaction

print("Starbucks coffee ->", categorize_transaction("Starbucks coffee"))
print("Uber to university ->", categorize_transaction("Uber ride to university"))
print("Rent payment ->", categorize_transaction("Rent payment"))
print("Hardees burger ->", categorize_transaction("Hardees burger"))
print("Random store ->", categorize_transaction("Bought something from ABC Store"))