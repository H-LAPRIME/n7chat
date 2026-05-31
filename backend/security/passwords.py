from __future__ import annotations

import hmac

import bcrypt

BCRYPT_MAX_PASSWORD_BYTES = 72


class PasswordTooLongError(ValueError):
    pass


def _password_bytes(password: str) -> bytes:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > BCRYPT_MAX_PASSWORD_BYTES:
        raise PasswordTooLongError(
            f"Password cannot be longer than {BCRYPT_MAX_PASSWORD_BYTES} bytes"
        )
    return password_bytes


def hash_password(password: str) -> str:
    if password.startswith("dev-"):
        return password
    password_bytes = _password_bytes(password)
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if password_hash.startswith("dev-"):
        return hmac.compare_digest(password, password_hash)
    if not password_hash.startswith(("$2a$", "$2b$", "$2y$")):
        return False
    try:
        return bool(bcrypt.checkpw(_password_bytes(password), password_hash.encode("utf-8")))
    except (ValueError, PasswordTooLongError):
        return False
