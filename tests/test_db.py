# tests/test_db.py
from db.connection import get_connection

try:
    connection = get_connection()
    print("✅ Connected using connection.py")

    cursor = connection.cursor()
    cursor.execute("SELECT table_name FROM user_tables")

    for row in cursor:
        print(row[0])

    cursor.close()
    connection.close()

except Exception as e:
    print("❌ Error:", e)