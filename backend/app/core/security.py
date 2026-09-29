import hashlib
import secrets
from datetime import UTC, datetime

from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()
# Verify a real Argon2 hash even when the account doesn't exist.
DUMMY_PASSWORD_HASH = password_hasher.hash(secrets.token_urlsafe(32))
SESSION_COOKIE = "visa_selfie_session"


def utcnow() -> datetime:
    return datetime.now(UTC)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(32)
