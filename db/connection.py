# tests/db/connection.py
import oracledb

def get_connection():
    return oracledb.connect(
        user="PFM_User",
        password="Abdallah25",
        dsn="LAPTOP-SUGN2H37:1521/XEPDB1"
    )