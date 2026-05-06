import json
import logging
import os
import signal
import socket
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from DistroChat.server.admin_manager import AdminManager
from DistroChat.server.auth_manager import AuthManager
from DistroChat.server.client_handler import ClientHandler
from DistroChat.server.db_manager import DBManager
from DistroChat.server.room_manager import RoomManager
from DistroChat.shared.protocol import build_message, encode_message, send_message


class ChatServer:
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.host = self.config.get("host", "0.0.0.0")
        self.port = int(self.config.get("port", 5050))
        self.max_clients = int(self.config.get("max_clients", 50))
        self.log_path = self.config.get("log_path", "logs/chat_logs.txt")
        self.room_capacity = int(self.config.get("room_max_capacity", 200))

        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        logging.basicConfig(
            level=getattr(logging, self.config.get("log_level", "INFO").upper(), logging.INFO),
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.FileHandler(self.log_path, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
        )
        self.logger = logging.getLogger("DistroChatServer")

        self.db = DBManager(self.config.get("db_path", "database/distrochat.db"))
        self.auth = AuthManager(self.db)
        self.room_manager = RoomManager(self.db, self.room_capacity)
        self.admin_manager = AdminManager(self)
        self._bootstrap_admin_if_configured()

        self.connected_clients: Dict[str, ClientHandler] = {}
        self._clients_lock = threading.Lock()
        self._running = threading.Event()
        self._running.set()
        self._executor = ThreadPoolExecutor(max_workers=min(50, self.max_clients))
        self._server_socket: Optional[socket.socket] = None
        self.started_at = time.time()

    def _bootstrap_admin_if_configured(self) -> None:
        b = self.config.get("admin_bootstrap") or {}
        if not b.get("enabled"):
            return
        username = str(b.get("username", "admin")).strip()
        password = str(b.get("password", ""))
        email = str(b.get("email", f"{username}@distrochat.local")).strip()
        if not username or not password:
            self.logger.warning("admin_bootstrap enabled but username/password missing")
            return
        if self.db.get_user(username):
            return
        try:
            import bcrypt

            hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        except Exception as exc:
            self.logger.error("admin_bootstrap bcrypt failed: %s", exc)
            return
        if self.db.register_user(username, hashed, email, role="admin"):
            self.logger.info("Created bootstrap admin user '%s' (change password in production)", username)
        else:
            self.logger.warning("Could not create bootstrap admin '%s' (already exists?)", username)

    def _load_config(self, path: str) -> dict:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def encode_plain(self, message: dict) -> bytes:
        return json.dumps(message, ensure_ascii=False).encode("utf-8")

    def send_plain(self, conn: socket.socket, message: dict) -> None:
        send_message(conn, message)

    def send_encrypted(self, conn: socket.socket, encrypted_payload: bytes) -> None:
        conn.sendall(len(encrypted_payload).to_bytes(4, "big") + encrypted_payload)

    def register_client(self, username: str, handler: ClientHandler) -> None:
        with self._clients_lock:
            self.connected_clients[username] = handler
        self.logger.info("Connected: %s (%s)", username, handler.addr)

    def unregister_client(self, username: str) -> None:
        with self._clients_lock:
            self.connected_clients.pop(username, None)
        self.logger.info("Disconnected: %s", username)

    def get_online_users(self) -> list[str]:
        with self._clients_lock:
            return sorted(self.connected_clients.keys())

    def live_stats_json(self, is_staff: bool = False, username: Optional[str] = None) -> str:
        if is_staff:
            stats = self.admin_manager.get_live_stats()
        else:
            stats = {
                "online_users": len(self.connected_clients),
                "messages_per_minute": self.admin_manager.messages_per_minute(),
                "room_activity": {r["name"]: r["members"] for r in self.room_manager.list_rooms(username)}
            }
            
        with self._clients_lock:
            users = []
            for username, handler in self.connected_clients.items():
                # For non-staff, we only show username and room
                if is_staff:
                    db_user = self.db.get_user(username) or {}
                    users.append({
                        "username": username,
                        "role": db_user.get("role", "user"),
                        "room": handler.current_room,
                        "ip": handler.addr[0],
                        "join_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(getattr(handler, "connected_at", None) or self.started_at)),
                    })
                else:
                    users.append({
                        "username": username,
                        "room": handler.current_room,
                    })
        stats["users"] = users
        stats["uptime_seconds"] = int(time.time() - self.started_at)
        return json.dumps(stats, ensure_ascii=False)

    def send_to_user(self, username: str, message: dict) -> None:
        with self._clients_lock:
            target = self.connected_clients.get(username)
        if target:
            target.send(message)

    def broadcast_room(self, room_name: str, message: dict, exclude: str = "") -> None:
        with self._clients_lock:
            handlers = list(self.connected_clients.items())
        room_members = self.room_manager.room_members.get(room_name, set())
        for username, handler in handlers:
            if username in room_members and username != exclude:
                handler.send(message)

    def broadcast_server_message(self, content: str) -> None:
        msg = build_message("server_msg", sender="server", room="#general", content=content)
        count = 0
        with self._clients_lock:
            handlers = list(self.connected_clients.values())
        
        for handler in handlers:
            try:
                handler.send(msg)
                count += 1
            except Exception as e:
                self.logger.error("Failed to send broadcast to %s: %s", getattr(handler, 'username', 'unknown'), e)
        
        self.logger.info("EVENT_LOG: Broadcast sent to %d users | Content: %s", count, content)

    def kick_user(self, username: str, reason: str) -> None:
        with self._clients_lock:
            handler = self.connected_clients.get(username)
        if handler:
            handler.send(build_message("kick", sender="server", content=reason))
            handler.disconnect(reason)

    def ban_user(self, actor: str, username: str, reason: str) -> None:
        self.db.ban_user(username, reason, actor)
        self.kick_user(username, f"Banned: {reason}")

    def start(self) -> None:
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(self.max_clients)
        self.logger.info(
            "Server started at %s:%s | Time: %s | Active connections: %s",
            self.host,
            self.port,
            time.strftime("%Y-%m-%d %H:%M:%S"),
            len(self.connected_clients),
        )
        self.logger.info("Waiting for clients...")
        while self._running.is_set():
            try:
                conn, addr = self._server_socket.accept()
                conn.settimeout(120)
                handler = ClientHandler(self, conn, addr)
                self._executor.submit(handler.run)
            except OSError:
                break
            except Exception as exc:
                self.logger.exception("Accept error: %s", exc)

    def shutdown(self) -> None:
        self._running.clear()
        self.logger.info("Graceful shutdown initiated...")
        with self._clients_lock:
            clients = list(self.connected_clients.values())
        for h in clients:
            h.disconnect("Server shutdown")
        if self._server_socket:
            try:
                self._server_socket.close()
            except OSError:
                pass
        self._executor.shutdown(wait=False, cancel_futures=True)
        self.logger.info("Shutdown complete.")


def main() -> None:
    server = ChatServer()

    def _stop(*_args: object) -> None:
        server.shutdown()

    signal.signal(signal.SIGINT, _stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _stop)
    try:
        server.start()
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()

