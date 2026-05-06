import base64
import hashlib
import json
import os
import socket
import threading
import time
from typing import Any, Callable, Dict, Optional

from DistroChat.shared.encryption import AESCipher
from DistroChat.shared.protocol import MessageType, build_message, decode_message, recv_packet


class ChatClient:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = int(port)
        self.sock: Optional[socket.socket] = None
        self.running = False
        self.recv_thread: Optional[threading.Thread] = None
        self.token = ""
        self.username = ""
        self.current_room = "#general"
        self.role = "user"
        self._cipher: Optional[AESCipher] = None
        self._send_lock = threading.Lock()

        self.on_message: Callable[[Dict[str, Any]], None] = lambda _m: None
        self.on_connect: Callable[[], None] = lambda: None
        self.on_disconnect: Callable[[str], None] = lambda _e: None
        self.on_error: Callable[[str], None] = lambda _e: None

    def connect(self) -> bool:
        attempts = 0
        while attempts < 3:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(10)
                self.sock.connect((self.host, self.port))
                self.sock.settimeout(None)
                first = recv_packet(self.sock)
                if not first:
                    raise ConnectionError("No handshake")
                hello = decode_message(first)
                key_b64 = hello.get("key", "")
                self._cipher = AESCipher.from_b64_key(key_b64)
                self.running = True
                self.recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
                self.recv_thread.start()
                self.on_connect()
                return True
            except Exception as exc:
                attempts += 1
                self.on_error(f"Connect failed ({attempts}/3): {exc}")
                time.sleep(2)
        return False

    def _send(self, msg: Dict[str, Any]) -> None:
        if not self.running or not self.sock or not self._cipher:
            return
        try:
            payload = json.dumps(msg, ensure_ascii=False).encode("utf-8")
            encrypted = self._cipher.encrypt(payload)
            packet = len(encrypted).to_bytes(4, "big") + encrypted
            with self._send_lock:
                self.sock.sendall(packet)
        except Exception as exc:
            self.on_error(f"Send error: {exc}")
            self.disconnect("send error")

    def _recv_loop(self) -> None:
        while self.running and self.sock:
            try:
                packet = recv_packet(self.sock)
                if not packet:
                    break
                if not self._cipher:
                    continue
                plain = self._cipher.decrypt(packet)
                msg = decode_message(plain)
                if msg.get("type") == MessageType.AUTH_OK:
                    self.token = msg.get("token", self.token)
                    self.role = msg.get("role", "user")
                    self.current_room = msg.get("room", "#general")
                elif msg.get("type") == MessageType.STATUS and msg.get("room"):
                    self.current_room = msg.get("room", self.current_room)
                self.on_message(msg)
            except Exception as exc:
                if self.running:
                    self.on_error(f"Receive error: {exc}")
                break
        self.disconnect("connection lost")

    def login(self, username: str, password: str) -> None:
        self.username = username
        self._send(
            {
                "type": MessageType.AUTH,
                "action": "login",
                "username": username,
                "password": password,
            }
        )

    def register(self, username: str, password: str, email: str) -> None:
        self._send(
            {
                "type": MessageType.AUTH,
                "action": "register",
                "username": username,
                "password": password,
                "email": email,
            }
        )

    def send_chat(self, content: str, room: Optional[str] = None) -> None:
        self._send(build_message(MessageType.CHAT, sender=self.username, room=room or self.current_room, content=content, token=self.token))

    def send_dm(self, target_user: str, content: str) -> None:
        m = build_message(MessageType.DM, sender=self.username, room="@dm", content=content, token=self.token, to=target_user)
        self._send(m)

    def join_room(self, room_name: str, password: str = "") -> None:
        self._send(build_message(MessageType.JOIN, sender=self.username, room=room_name, token=self.token, password=password))

    def leave_room(self, room_name: Optional[str] = None) -> None:
        self._send(build_message(MessageType.LEAVE, sender=self.username, room=room_name or self.current_room, token=self.token))

    def send_command(self, command_text: str) -> None:
        self._send(build_message(MessageType.COMMAND, sender=self.username, room=self.current_room, content=command_text, token=self.token))

    def send_typing(self) -> None:
        self._send(build_message(MessageType.TYPING, sender=self.username, room=self.current_room, content="typing", token=self.token))

    def send_file(self, path: str, room: Optional[str] = None) -> None:
        if not os.path.exists(path):
            self.on_error("File not found")
            return
        file_size = os.path.getsize(path)
        if file_size > 5 * 1024 * 1024:
            self.on_error("File too large (max 5MB)")
            return
        ext = os.path.splitext(path)[1].lower()
        if ext not in (".png", ".jpg", ".jpeg"):
            self.on_error("Only PNG/JPG allowed")
            return
        with open(path, "rb") as f:
            raw = f.read()
        data = base64.b64encode(raw).decode("utf-8")
        file_hash = hashlib.sha256(raw).hexdigest()
        m = build_message(
            MessageType.FILE,
            sender=self.username,
            room=room or self.current_room,
            content=f"file:{os.path.basename(path)}",
            token=self.token,
            file_name=os.path.basename(path),
            file_data=data,
            file_size=file_size,
            file_hash=file_hash,
        )
        self._send(m)

    def disconnect(self, reason: str = "manual") -> None:
        if not self.running:
            return
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None
        self.on_disconnect(reason)

