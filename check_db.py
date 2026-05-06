import sqlite3
import os

db_path = r"c:\Users\montafe\Downloads\Compressed\testtt\database\distrochat.db"
if not os.path.exists(db_path):
    print("Database not found")
else:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        cur.execute("SELECT username, password_hash, role FROM users")
        rows = cur.fetchall()
        for row in rows:
            print(f"User: {row['username']}, Role: {row['role']}, Hash: {row['password_hash']}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
