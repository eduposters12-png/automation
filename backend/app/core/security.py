import base64
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
    except JWTError:
        return None


def _encryption_key() -> bytes:
    raw_key = get_settings().encryption_key.strip()
    try:
        if len(raw_key) == 64:
            return bytes.fromhex(raw_key)
    except ValueError:
        pass

    encoded = raw_key.encode("utf-8")
    if len(encoded) == 32:
        return encoded

    raise ValueError(
        "ENCRYPTION_KEY must be 32 raw bytes or 64 hex characters "
        "(generate with: openssl rand -hex 32)."
    )


def encrypt_secret(plain_text: str) -> str:
    if not plain_text:
        return ""

    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(_encryption_key()), modes.CBC(iv))
    encryptor = cipher.encryptor()
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plain_text.encode("utf-8")) + padder.finalize()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    return (
        f"{base64.urlsafe_b64encode(iv).decode('utf-8')}:"
        f"{base64.urlsafe_b64encode(ciphertext).decode('utf-8')}"
    )


def decrypt_secret(encrypted_text: str) -> str:
    if not encrypted_text:
        return ""

    iv_text, ciphertext_text = encrypted_text.split(":", 1)
    iv = base64.urlsafe_b64decode(iv_text.encode("utf-8"))
    ciphertext = base64.urlsafe_b64decode(ciphertext_text.encode("utf-8"))
    cipher = Cipher(algorithms.AES(_encryption_key()), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    plain = unpadder.update(padded) + unpadder.finalize()
    return plain.decode("utf-8")
