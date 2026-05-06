import threading
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple

import bcrypt

from DistroChat.server.db_manager import DBManager


class RoomManager:
    def __init__(self, db: DBManager, default_capacity: int = 200):
        self.db = db
        self.default_capacity = default_capacity
        self._lock = threading.Lock()
        self.rooms: Dict[str, Dict[str, Any]] = {}
        self.room_members: Dict[str, Set[str]] = defaultdict(set)
        self.room_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=50))
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        defaults = [
            ("#general", "General discussion", "system"),
            ("#random", "Random chat", "system"),
            ("#announcements", "Official announcements", "system"),
        ]
        for name, desc, owner in defaults:
            self.db.create_room(name, desc, owner, False, "", self.default_capacity)
        for room in self.db.list_rooms():
            self.rooms[room["name"]] = room

    def create_room(
        self,
        name: str,
        description: str,
        created_by: str,
        is_private: bool = False,
        password: str = "",
        max_capacity: Optional[int] = None,
    ) -> Tuple[bool, str]:
        name = self._normalize_room(name)
        with self._lock:
            if name in self.rooms:
                return False, "Room already exists"
            pw_hash = ""
            if is_private and password:
                pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            cap = max_capacity or self.default_capacity
            ok = self.db.create_room(name, description, created_by, is_private, pw_hash, cap)
            if not ok:
                return False, "Cannot create room"
            room = next((r for r in self.db.list_rooms() if r["name"] == name), None)
            if room:
                self.rooms[name] = room
                # Automatically add creator to the room membership in DB
                self.db.add_user_to_room(created_by, name)
            return True, f"Room {name} created"

    def delete_room(self, name: str) -> bool:
        with self._lock:
            if name in ("#general", "#random", "#announcements"):
                return False
            if name in self.rooms:
                del self.rooms[name]
                self.room_members.pop(name, None)
                self.room_history.pop(name, None)
                return True
            return False

    def list_rooms(self, username: Optional[str] = None, show_all: bool = False) -> List[Dict[str, Any]]:
        with self._lock:
            out = []
            user_joined_rooms = set()
            if username:
                user_joined_rooms = set(self.db.get_user_rooms(username))
                # Also include rooms they are currently in (in-memory)
                for rname, members in self.room_members.items():
                    if username in members:
                        user_joined_rooms.add(rname)

            for room_name, room in self.rooms.items():
                is_private = bool(room.get("is_private", 0))
                owner = room.get("created_by", "")
                
                # Logic: show if show_all (admin) OR public OR if user is owner OR if user has ever joined
                should_show = show_all or not is_private or (username and (username == owner or room_name in user_joined_rooms))
                
                if should_show:
                    out.append(
                        {
                            "name": room_name,
                            "description": room.get("description", ""),
                            "is_private": is_private,
                            "members": len(self.room_members.get(room_name, set())),
                            "max_capacity": room.get("max_capacity", self.default_capacity),
                        }
                    )
            return sorted(out, key=lambda r: r["name"])

    def join_room(self, username: str, room_name: str, password: str = "") -> Tuple[bool, str]:
        room_name = self._normalize_room(room_name)
        with self._lock:
            room = self.rooms.get(room_name)
            if not room:
                return False, "Room not found"
            members = self.room_members[room_name]
            if len(members) >= int(room.get("max_capacity", self.default_capacity)):
                return False, "Room is full"
            if bool(room.get("is_private", 0)):
                # Bypass password for owner or if already joined (persistence)
                is_owner = (room.get("created_by") == username)
                user_rooms = self.db.get_user_rooms(username)
                
                if not is_owner and room_name not in user_rooms:
                    pw_hash = room.get("password_hash") or ""
                    if not pw_hash or not password or not bcrypt.checkpw(password.encode("utf-8"), pw_hash.encode("utf-8")):
                        return False, "Invalid room password"
            members.add(username)
            # Persist join for "stay open" feature
            self.db.add_user_to_room(username, room_name)
            return True, f"{username} joined {room_name}"

    def leave_room(self, username: str, room_name: str) -> Tuple[bool, str]:
        room_name = self._normalize_room(room_name)
        with self._lock:
            if room_name not in self.room_members:
                return False, "Room not found"
            self.room_members[room_name].discard(username)
            return True, f"{username} left {room_name}"

    def _normalize_room(self, room_name: str) -> str:
        room = room_name.strip()
        if room and not room.startswith("#"):
            room = f"#{room}"
        return room

    def add_history(self, room_name: str, message: Dict[str, Any]) -> None:
        with self._lock:
            self.room_history[room_name].append(message)

    def get_history(self, room_name: str) -> List[Dict[str, Any]]:
        with self._lock:
            in_memory = list(self.room_history.get(room_name, deque()))
        if in_memory:
            return in_memory[-50:]
        return self.db.get_history(room_name, limit=50)

    def clear_room(self, room_name: str) -> None:
        with self._lock:
            if room_name in self.room_history:
                self.room_history[room_name].clear()
        self.db.clear_room_history(room_name)

    def room_activity(self) -> Dict[str, int]:
        with self._lock:
            return {name: len(users) for name, users in self.room_members.items()}

