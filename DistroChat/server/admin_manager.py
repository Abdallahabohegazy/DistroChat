import threading
import time
from collections import deque
from typing import Dict, Tuple


class AdminManager:
    def __init__(self, server: "ChatServer"):
        self.server = server
        self._recent_messages = deque(maxlen=1200)
        self._mute_map: Dict[str, float] = {}
        self._lock = threading.Lock()

    def track_message(self) -> None:
        with self._lock:
            self._recent_messages.append(time.time())

    def messages_per_minute(self) -> int:
        now = time.time()
        with self._lock:
            while self._recent_messages and now - self._recent_messages[0] > 60:
                self._recent_messages.popleft()
            return len(self._recent_messages)

    def is_muted(self, username: str) -> bool:
        with self._lock:
            until = self._mute_map.get(username, 0)
            if until < time.time():
                self._mute_map.pop(username, None)
                return False
            return True

    def parse_command(self, actor: str, command: str, room: str = "") -> Tuple[bool, str]:
        parts = command.strip().split()
        if not parts:
            return False, "Empty command"
        cmd = parts[0].lower()
        if cmd == "/kick" and len(parts) >= 2:
            target = parts[1]
            self.server.kick_user(target, f"Kicked by {actor}")
            return True, f"{target} kicked"
        if cmd == "/ban" and len(parts) >= 2:
            target = parts[1]
            reason = " ".join(parts[2:]) if len(parts) > 2 else "No reason"
            self.server.ban_user(actor, target, reason)
            return True, f"{target} banned"
        if cmd == "/unban" and len(parts) >= 2:
            self.server.db.unban_user(parts[1])
            return True, f"{parts[1]} unbanned"
        if cmd == "/mute" and len(parts) >= 3:
            target = parts[1]
            seconds = int(parts[2])
            with self._lock:
                self._mute_map[target] = time.time() + seconds
            return True, f"{target} muted for {seconds}s"
        if cmd == "/broadcast" and len(parts) >= 2:
            text = " ".join(parts[1:])
            self.server.broadcast_server_message(text)
            return True, "Broadcast sent"
        if cmd == "/promote" and len(parts) >= 2:
            ok = self.server.db.promote_to_moderator(parts[1])
            return ok, "Promoted" if ok else "User not found"
        if cmd == "/clear_room":
            target_room = parts[1] if len(parts) > 1 else room
            if not target_room:
                return False, "No room specified"
            self.server.room_manager.clear_room(target_room)
            # Broadcast to all users in room to clear their UI
            self.server.broadcast_room(target_room, {"type": "server_msg", "sender": "server", "room": target_room, "content": "CLEAR_UI"})
            return True, f"Room {target_room} history cleared"
        return False, "Unknown command"

    def get_live_stats(self) -> Dict[str, object]:
        return {
            "online_users": len(self.server.connected_clients),
            "messages_per_minute": self.messages_per_minute(),
            "room_activity": {r["name"]: r["members"] for r in self.server.room_manager.list_rooms(show_all=True)},
            "db_stats": self.server.db.get_stats(),
        }

