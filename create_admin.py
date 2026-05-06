import sqlite3
import os
import bcrypt
import time

# Configuration
DB_PATH = r"database/distrochat.db"
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"
ADMIN_EMAIL = "admin@distrochat.local"

def create_admin():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    # Hash the password
    print(f"Hashing password for user '{ADMIN_USER}'...")
    hashed = bcrypt.hashpw(ADMIN_PASS.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # Connect to DB
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        # Check if user already exists
        cur.execute("SELECT id FROM users WHERE username = ?", (ADMIN_USER,))
        if cur.fetchone():
            print(f"User '{ADMIN_USER}' already exists. Updating role to admin and resetting password...")
            cur.execute(
                "UPDATE users SET password_hash = ?, role = 'admin' WHERE username = ?",
                (hashed, ADMIN_USER)
            )
        else:
            print(f"Creating new admin user '{ADMIN_USER}'...")
            cur.execute(
                "INSERT INTO users (username, password_hash, email, role, created_at) VALUES (?, ?, ?, ?, ?)",
                (ADMIN_USER, hashed, ADMIN_EMAIL, "admin", time.strftime("%Y-%m-%d %H:%M:%S"))
            )
        
        conn.commit()
        print("Successfully created/updated admin credentials!")
        print(f"Username: {ADMIN_USER}")
        print(f"Password: {ADMIN_PASS}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_admin()
