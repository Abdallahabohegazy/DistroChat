import base64
import os
from hashlib import sha256

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class AESCipher:
    def __init__(self, raw_key: bytes):
        self._key = sha256(raw_key).digest()[:16]
        self._aes = AESGCM(self._key)

    @classmethod
    def from_b64_key(cls, key_b64: str) -> "AESCipher":
        return cls(base64.b64decode(key_b64.encode("utf-8")))

    @staticmethod
    def generate_key_b64() -> str:
        return base64.b64encode(os.urandom(16)).decode("utf-8")

    def encrypt(self, message: bytes) -> bytes:
        nonce = os.urandom(12)
        cipher = self._aes.encrypt(nonce, message, None)
        return nonce + cipher

    def decrypt(self, encrypted_message: bytes) -> bytes:
        nonce = encrypted_message[:12]
        body = encrypted_message[12:]
        return self._aes.decrypt(nonce, body, None)


def encrypt_text(text: str, key_b64: str) -> str:
    cipher = AESCipher.from_b64_key(key_b64)
    return base64.b64encode(cipher.encrypt(text.encode("utf-8"))).decode("utf-8")


def decrypt_text(payload_b64: str, key_b64: str) -> str:
    cipher = AESCipher.from_b64_key(key_b64)
    raw = base64.b64decode(payload_b64.encode("utf-8"))
    return cipher.decrypt(raw).decode("utf-8")

