import uuid
from typing import Dict, Optional, Tuple

import bcrypt

from DistroChat.server.db_manager import DBManager


class AuthManager:
    def __init__(self, db: DBManager):
        self.db = db
        self.sessions: Dict[str, str] = {}

    def register(self, username: str, password: str, email: str) -> Tuple[bool, str]:
        if len(username) < 3 or len(password) < 6:
            return False, "Username or password too short"
        if self.db.is_banned(username):
            return False, "User is banned"
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        ok = self.db.register_user(username, hashed, email)
        return (True, "Registered") if ok else (False, "Username or email already exists")

    def login(self, username: str, password: str) -> Tuple[bool, str, str]:
        if self.db.is_banned(username):
            return False, "", "User is banned"
        user = self.db.get_user(username)
        if not user:
            return False, "", "User not found"
        if not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
            return False, "", "Invalid password"
        token = str(uuid.uuid4())
        self.sessions[token] = username
        return True, token, "Login successful"

    def verify_token(self, token: str) -> Optional[str]:
        return self.sessions.get(token)

    def logout(self, token: str) -> None:
        if token in self.sessions:
            del self.sessions[token]

