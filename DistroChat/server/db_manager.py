import os
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional


class DBManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA busy_timeout=30000;")
        return con

    def _init_db(self) -> None:
        with self._lock:
            con = self._connect()
            cur = con.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    created_at TEXT NOT NULL,
                    last_seen TEXT,
                    last_room TEXT DEFAULT '#general'
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    room TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    is_dm INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS rooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_by TEXT,
                    is_private INTEGER NOT NULL DEFAULT 0,
                    password_hash TEXT,
                    max_capacity INTEGER NOT NULL DEFAULT 200
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_rooms (
                    username TEXT NOT NULL,
                    room_name TEXT NOT NULL,
                    PRIMARY KEY (username, room_name)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS banned_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    reason TEXT,
                    banned_by TEXT,
                    banned_at TEXT NOT NULL
                )
                """
            )
            con.commit()
            con.close()

    def register_user(self, username: str, password_hash: str, email: str, role: str = "user") -> bool:
        with self._lock:
            con = self._connect()
            try:
                con.execute(
                    "INSERT INTO users (username, password_hash, email, role, created_at) VALUES (?, ?, ?, ?, ?)",
                    (username, password_hash, email, role, time.strftime("%Y-%m-%d %H:%M:%S")),
                )
                con.commit()
                return True
            except sqlite3.IntegrityError:
                return False
            finally:
                con.close()

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            con = self._connect()
            row = con.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            con.close()
        return dict(row) if row else None

    def update_last_seen(self, username: str, last_room: Optional[str] = None) -> None:
        with self._lock:
            con = self._connect()
            if last_room:
                con.execute(
                    "UPDATE users SET last_seen = ?, last_room = ? WHERE username = ?",
                    (time.strftime("%Y-%m-%d %H:%M:%S"), last_room, username),
                )
            else:
                con.execute(
                    "UPDATE users SET last_seen = ? WHERE username = ?",
                    (time.strftime("%Y-%m-%d %H:%M:%S"), username),
                )
            con.commit()
            con.close()

    def save_message(self, sender: str, room: str, content: str, timestamp: str, is_dm: bool = False) -> None:
        with self._lock:
            con = self._connect()
            con.execute(
                "INSERT INTO messages (sender, room, content, timestamp, is_dm) VALUES (?, ?, ?, ?, ?)",
                (sender, room, content, timestamp, int(is_dm)),
            )
            con.commit()
            con.close()

    def get_history(self, room: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            con = self._connect()
            rows = con.execute(
                "SELECT sender, room, content, timestamp, is_dm FROM messages WHERE room = ? ORDER BY id DESC LIMIT ?",
                (room, limit),
            ).fetchall()
            con.close()
        return [dict(r) for r in reversed(rows)]

    def clear_room_history(self, room: str) -> None:
        with self._lock:
            con = self._connect()
            con.execute("DELETE FROM messages WHERE room = ?", (room,))
            con.commit()
            con.close()

    def create_room(
        self,
        name: str,
        description: str,
        created_by: str,
        is_private: bool = False,
        password_hash: str = "",
        max_capacity: int = 200,
    ) -> bool:
        with self._lock:
            con = self._connect()
            try:
                con.execute(
                    "INSERT INTO rooms (name, description, created_by, is_private, password_hash, max_capacity) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, description, created_by, int(is_private), password_hash, max_capacity),
                )
                con.commit()
                return True
            except sqlite3.IntegrityError:
                return False
            finally:
                con.close()

    def list_rooms(self) -> List[Dict[str, Any]]:
        with self._lock:
            con = self._connect()
            rows = con.execute("SELECT * FROM rooms ORDER BY name ASC").fetchall()
            con.close()
        return [dict(r) for r in rows]

    def add_user_to_room(self, username: str, room_name: str) -> None:
        with self._lock:
            con = self._connect()
            con.execute("INSERT OR IGNORE INTO user_rooms (username, room_name) VALUES (?, ?)", (username, room_name))
            con.commit()
            con.close()

    def get_user_rooms(self, username: str) -> List[str]:
        with self._lock:
            con = self._connect()
            rows = con.execute("SELECT room_name FROM user_rooms WHERE username = ?", (username,)).fetchall()
            con.close()
        return [r["room_name"] for r in rows]

    def ban_user(self, username: str, reason: str, banned_by: str) -> None:
        with self._lock:
            con = self._connect()
            con.execute(
                "INSERT OR REPLACE INTO banned_users (username, reason, banned_by, banned_at) VALUES (?, ?, ?, ?)",
                (username, reason, banned_by, time.strftime("%Y-%m-%d %H:%M:%S")),
            )
            con.commit()
            con.close()

    def unban_user(self, username: str) -> None:
        with self._lock:
            con = self._connect()
            con.execute("DELETE FROM banned_users WHERE username = ?", (username,))
            con.commit()
            con.close()

    def is_banned(self, username: str) -> bool:
        with self._lock:
            con = self._connect()
            row = con.execute("SELECT id FROM banned_users WHERE username = ?", (username,)).fetchone()
            con.close()
        return row is not None

    def promote_to_moderator(self, username: str) -> bool:
        with self._lock:
            con = self._connect()
            cur = con.execute("UPDATE users SET role = 'moderator' WHERE username = ?", (username,))
            con.commit()
            changed = cur.rowcount > 0
            con.close()
        return changed

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            con = self._connect()
            cur = con.cursor()
            total_users = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            total_messages = cur.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            total_rooms = cur.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
            banned = cur.execute("SELECT COUNT(*) FROM banned_users").fetchone()[0]
            con.close()
        return {
            "total_users": total_users,
            "total_messages": total_messages,
            "total_rooms": total_rooms,
            "banned_users": banned,
        }

