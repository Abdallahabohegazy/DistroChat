import json
import socket
import struct
import time
from enum import StrEnum
from typing import Any, Dict, Optional


HEADER_SIZE = 4


class MessageType(StrEnum):
    CHAT = "chat"
    DM = "dm"
    JOIN = "join_room"
    LEAVE = "leave_room"
    AUTH = "auth"
    AUTH_OK = "auth_ok"
    AUTH_FAIL = "auth_fail"
    KICK = "kick"
    BAN = "ban"
    TYPING = "typing"
    STATUS = "status"
    FILE = "file"
    ERROR = "error"
    SERVER_MSG = "server_msg"
    COMMAND = "command"


def now_hms() -> str:
    return time.strftime("%H:%M:%S")


def build_message(
    msg_type: str,
    sender: str = "",
    room: str = "",
    content: str = "",
    token: str = "",
    **extra: Any,
) -> Dict[str, Any]:
    msg = {
        "type": msg_type,
        "sender": sender,
        "room": room,
        "content": content,
        "timestamp": now_hms(),
        "token": token,
    }
    msg.update(extra)
    return msg


def encode_message(message: Dict[str, Any]) -> bytes:
    raw = json.dumps(message, ensure_ascii=False).encode("utf-8")
    return struct.pack("!I", len(raw)) + raw


def _recv_exact(sock: socket.socket, size: int) -> Optional[bytes]:
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def recv_packet(sock: socket.socket) -> Optional[bytes]:
    header = _recv_exact(sock, HEADER_SIZE)
    if not header:
        return None
    length = struct.unpack("!I", header)[0]
    if length <= 0 or length > 20 * 1024 * 1024:
        return None
    return _recv_exact(sock, length)


def decode_message(packet: bytes) -> Dict[str, Any]:
    return json.loads(packet.decode("utf-8"))


def send_message(sock: socket.socket, message: Dict[str, Any]) -> None:
    sock.sendall(encode_message(message))

