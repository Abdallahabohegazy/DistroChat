import base64
import hashlib
import os
import shlex
import socket
import threading
import time
from typing import Any, Dict, Optional

from DistroChat.shared.encryption import AESCipher
from DistroChat.shared.protocol import MessageType, build_message, decode_message, recv_packet


class ClientHandler:
    def __init__(self, server: "ChatServer", conn: socket.socket, addr: tuple[str, int]):
        self.server = server
        self.conn = conn
        self.addr = addr
        self.username: str = ""
        self.token: str = ""
        self.current_room = "#general"
        self.connected_at: float = 0.0
        self.alive = True
        self.role = "guest"
        self.last_seen = time.time()
        self._send_lock = threading.Lock()
        key_b64 = AESCipher.generate_key_b64()
        self._cipher = AESCipher.from_b64_key(key_b64)
        self._session_key_b64 = key_b64

    def run(self) -> None:
        try:
            self.server.send_plain(
                self.conn,
                build_message(MessageType.SERVER_MSG, sender="server", content="key_exchange", key=self._session_key_b64),
            )
            while self.alive:
                packet = recv_packet(self.conn)
                if not packet:
                    break
                try:
                    plain = self._cipher.decrypt(packet)
                    msg = decode_message(plain)
                except Exception:
                    self.send(build_message(MessageType.ERROR, sender="server", content="Invalid encrypted packet"))
                    continue
                self.last_seen = time.time()
                if self.username:
                    self.server.db.update_last_seen(self.username, self.current_room)
                self.handle_message(msg)
        except (OSError, ConnectionError):
            pass
        finally:
            self.disconnect("Client disconnected")

    def send(self, message: Dict[str, Any]) -> None:
        if not self.alive:
            return
        try:
            payload = self._cipher.encrypt(self.server.encode_plain(message))
            with self._send_lock:
                self.server.send_encrypted(self.conn, payload)
        except OSError:
            self.disconnect("Send failed")

    def handle_message(self, msg: Dict[str, Any]) -> None:
        msg_type = msg.get("type")
        if msg_type == MessageType.AUTH:
            self._handle_auth(msg)
        elif msg_type == MessageType.CHAT:
            self._handle_chat(msg)
        elif msg_type == MessageType.DM:
            self._handle_dm(msg)
        elif msg_type == MessageType.JOIN:
            self._handle_join(msg)
        elif msg_type == MessageType.LEAVE:
            self._handle_leave(msg)
        elif msg_type == MessageType.COMMAND:
            self._handle_command(msg)
        elif msg_type == MessageType.FILE:
            self._handle_file(msg)
        elif msg_type in (MessageType.TYPING, MessageType.STATUS):
            self.server.broadcast_room(self.current_room, msg, exclude=self.username)
        else:
            self.send(build_message(MessageType.ERROR, sender="server", content=f"Unknown type: {msg_type}"))

    def _handle_auth(self, msg: Dict[str, Any]) -> None:
        action = msg.get("action", "login")
        username = msg.get("username", "").strip()
        password = msg.get("password", "")
        email = msg.get("email", "")
        if action == "register":
            ok, text = self.server.auth.register(username, password, email)
            reply = MessageType.AUTH_OK if ok else MessageType.AUTH_FAIL
            self.send(build_message(reply, sender="server", content=text))
            return
        ok, token, text = self.server.auth.login(username, password)
        if not ok:
            self.send(build_message(MessageType.AUTH_FAIL, sender="server", content=text))
            return
        self.username = username
        self.token = token
        user = self.server.db.get_user(self.username) or {}
        self.role = user.get("role", "user")
        self.connected_at = time.time()
        self.server.register_client(self.username, self)
        desired_room = user.get("last_room", "#general")
        joined, _ = self.server.room_manager.join_room(self.username, desired_room)
        self.current_room = desired_room if joined else "#general"
        if not joined:
            self.server.room_manager.join_room(self.username, self.current_room)
        self.send(
            build_message(
                MessageType.AUTH_OK,
                sender="server",
                content=text,
                token=token,
                role=user.get("role", "user"),
                room=self.current_room,
            )
        )
        self.server.broadcast_server_message(f"{self.username} connected")
        self._send_room_history(self.current_room)

    def _role(self) -> str:
        return self.role

    def _is_staff(self) -> bool:
        return self._role() in ("admin", "moderator")

    def _is_admin(self) -> bool:
        return self._role() == "admin"

    def _authorized(self, msg: Dict[str, Any]) -> bool:
        token = msg.get("token", "")
        if not self.username or not token or self.server.auth.verify_token(token) != self.username:
            self.send(build_message(MessageType.AUTH_FAIL, sender="server", content="Auth required"))
            return False
        return True

    def _handle_chat(self, msg: Dict[str, Any]) -> None:
        if not self._authorized(msg):
            return
        if self.server.admin_manager.is_muted(self.username):
            self.send(build_message(MessageType.ERROR, sender="server", content="You are muted"))
            return
        room = msg.get("room") or self.current_room
        content = str(msg.get("content", "")).strip()
        if not content:
            return
        out = build_message(MessageType.CHAT, sender=self.username, room=room, content=content, token=self.token)
        self.server.db.save_message(self.username, room, content, out["timestamp"], is_dm=False)
        self.server.room_manager.add_history(room, out)
        self.server.admin_manager.track_message()
        self.server.broadcast_room(room, out)

    def _handle_dm(self, msg: Dict[str, Any]) -> None:
        if not self._authorized(msg):
            return
        target = msg.get("to", "").strip()
        content = str(msg.get("content", "")).strip()
        if not target or not content:
            return
        out = build_message(MessageType.DM, sender=self.username, room="@dm", content=content, token=self.token, to=target)
        self.server.db.save_message(self.username, "@dm", f"to={target}:{content}", out["timestamp"], is_dm=True)
        self.server.admin_manager.track_message()
        self.send(out)
        self.server.send_to_user(target, out)

    def _handle_join(self, msg: Dict[str, Any]) -> None:
        if not self._authorized(msg):
            return
        room = msg.get("room", "").strip()
        password = msg.get("password", "")
        ok, text = self.server.room_manager.join_room(self.username, room, password)
        if not ok:
            self.send(build_message(MessageType.ERROR, sender="server", content=text))
            return
        old_room = self.current_room
        self.server.room_manager.leave_room(self.username, old_room)
        self.current_room = room
        self.server.db.update_last_seen(self.username, room)
        self.send(build_message(MessageType.STATUS, sender="server", room=room, content=text))
        self.server.broadcast_room(room, build_message(MessageType.SERVER_MSG, sender="server", room=room, content=f"{self.username} joined"))
        self._send_room_history(room)

    def _handle_leave(self, msg: Dict[str, Any]) -> None:
        if not self._authorized(msg):
            return
        room = msg.get("room", self.current_room)
        self.server.room_manager.leave_room(self.username, room)
        self.current_room = "#general"
        self.server.room_manager.join_room(self.username, self.current_room)
        self.send(build_message(MessageType.STATUS, sender="server", room=self.current_room, content=f"Moved to {self.current_room}"))

    def _handle_command(self, msg: Dict[str, Any]) -> None:
        if not self._authorized(msg):
            return
        command = msg.get("content", "")
        c = command.strip()
        if c == "/help":
            self.send(
                build_message(
                    MessageType.SERVER_MSG,
                    sender="server",
                    content="/help /dm @user msg /rooms /who /clear /quit /join room [pw] /stats /kick /ban /unban /mute /broadcast",
                )
            )
            return
        if c == "/rooms":
            rooms = self.server.room_manager.list_rooms(username=self.username, show_all=self._is_staff())
            text = ", ".join([f"{r['name']}({r['members']})" for r in rooms])
            self.send(build_message(MessageType.SERVER_MSG, sender="server", content=text or "No rooms"))
            return
        if c == "/who":
            text = ", ".join(self.server.get_online_users())
            self.send(build_message(MessageType.SERVER_MSG, sender="server", content=text or "No users online"))
            return
        if c == "/stats":
            self.send(build_message(MessageType.SERVER_MSG, sender="server", content=self.server.live_stats_json(is_staff=self._is_staff(), username=self.username)))
            return
        if c.startswith("/join "):
            parts = c.split(" ", 2)
            room = parts[1]
            pw = parts[2] if len(parts) > 2 else ""
            self._handle_join({"type": MessageType.JOIN, "room": room, "password": pw, "token": self.token})
            return
        if c.startswith("/create_room "):
            try:
                parts = shlex.split(c)
            except ValueError:
                self.send(build_message(MessageType.ERROR, sender="server", content="Invalid room command format"))
                return
            if len(parts) < 2:
                self.send(build_message(MessageType.ERROR, sender="server", content="Usage: /create_room <name> [description] [--private <password>]"))
                return
            is_private = False
            password = ""
            if "--private" in parts:
                idx = parts.index("--private")
                is_private = True
                if idx + 1 < len(parts):
                    password = parts[idx + 1]
                parts = parts[:idx]
            name = parts[1]
            desc = " ".join(parts[2:]) if len(parts) > 2 else ""
            ok, text = self.server.room_manager.create_room(name, desc, self.username, is_private=is_private, password=password)
            if ok:
                # Auto-join the created room
                self._handle_join({"type": MessageType.JOIN, "room": name, "password": password, "token": self.token})
            mtype = MessageType.SERVER_MSG if ok else MessageType.ERROR
            self.send(build_message(mtype, sender="server", content=text))
            return
        if c.startswith("/dm "):
            parts = c.split(" ", 2)
            if len(parts) == 3:
                target = parts[1].lstrip("@")
                self._handle_dm({"type": MessageType.DM, "to": target, "content": parts[2], "token": self.token})
            return
        staff_cmds = {"/kick", "/ban", "/unban", "/mute", "/broadcast", "/promote", "/clear_room"}
        admin_only_cmds = {"/ban", "/unban", "/promote"}
        first = c.split(None, 1)[0].lower() if c else ""
        if first in staff_cmds:
            if not self._is_staff():
                self.send(build_message(MessageType.ERROR, sender="server", content="Permission denied"))
                return
            if first in admin_only_cmds and not self._is_admin():
                self.send(build_message(MessageType.ERROR, sender="server", content="Admin only"))
                return
        ok, text = self.server.admin_manager.parse_command(self.username, command, self.current_room)
        mtype = MessageType.SERVER_MSG if ok else MessageType.ERROR
        self.send(build_message(mtype, sender="server", content=text))

    def _handle_file(self, msg: Dict[str, Any]) -> None:
        if not self._authorized(msg):
            return
        room = msg.get("room", self.current_room)
        file_name = os.path.basename(str(msg.get("file_name", "")).strip())
        payload = msg.get("file_data", "")
        file_size = int(msg.get("file_size", 0) or 0)
        client_hash = str(msg.get("file_hash", "")).strip().lower()
        ext = os.path.splitext(file_name)[1].lower()
        if ext not in (".png", ".jpg", ".jpeg"):
            self.send(build_message(MessageType.ERROR, sender="server", content="Only PNG/JPG files are allowed"))
            return
        if not file_name:
            self.send(build_message(MessageType.ERROR, sender="server", content="Missing file name"))
            return
        try:
            raw = base64.b64decode(payload.encode("utf-8"))
        except Exception:
            self.send(build_message(MessageType.ERROR, sender="server", content="Invalid file"))
            return
        if len(raw) > 5 * 1024 * 1024:
            self.send(build_message(MessageType.ERROR, sender="server", content="File exceeds 5MB"))
            return
        if file_size and file_size != len(raw):
            self.send(build_message(MessageType.ERROR, sender="server", content="File size mismatch"))
            return
        server_hash = hashlib.sha256(raw).hexdigest()
        if client_hash and client_hash != server_hash:
            self.send(build_message(MessageType.ERROR, sender="server", content="File integrity check failed"))
            return
        out = build_message(
            MessageType.FILE,
            sender=self.username,
            room=room,
            content=f"file:{file_name}",
            file_name=file_name,
            file_data=payload,
            file_size=len(raw),
            file_hash=server_hash,
            token=self.token,
        )
        self.server.admin_manager.track_message()
        self.server.broadcast_room(room, out)

    def _send_room_history(self, room: str) -> None:
        history = self.server.room_manager.get_history(room)
        if history:
            self.send(build_message(MessageType.SERVER_MSG, sender="server", room=room, content="[History]"))
            for item in history:
                self.send(item)

    def disconnect(self, reason: str) -> None:
        if not self.alive:
            return
        self.alive = False
        try:
            self.conn.close()
        except OSError:
            pass
        if self.username:
            self.server.unregister_client(self.username)
            self.server.auth.logout(self.token)
            self.server.room_manager.leave_room(self.username, self.current_room)
            self.server.broadcast_server_message(f"{self.username} disconnected: {reason}")

