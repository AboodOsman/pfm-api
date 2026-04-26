from db.firebase import get_db

db = get_db()
print("Firebase connected:", db)