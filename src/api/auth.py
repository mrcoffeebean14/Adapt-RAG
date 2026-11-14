"""
Password hashing (scrypt) and stateless HMAC-signed login tokens. Stdlib only.
"""

import hashlib
import hmac
import os
import time

from src.core.config import settings

_KEY = settings.SECRET_KEY.encode()
TOKEN_TTL = 7 * 24 * 3600  # seconds


def _scrypt(password: str, salt: bytes) -> str:
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1).hex()


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    return f"{salt.hex()}${_scrypt(password, salt)}"


def verify_password(password: str, stored: str) -> bool:
    salt, digest = stored.split("$")
    return hmac.compare_digest(_scrypt(password, bytes.fromhex(salt)), digest)


def _sign(username: str) -> str:
    return hmac.new(_KEY, username.encode(), hashlib.sha256).hexdigest()


# ponytail: no server-side revocation; add a per-user token version to the payload if logout-everywhere is needed.
def make_token(username: str, now: float | None = None) -> str:
    """`username.expiry.signature`, valid for TOKEN_TTL."""
    payload = f"{username}.{int((now or time.time()) + TOKEN_TTL)}"
    return f"{payload}.{_sign(payload)}"


def user_from_token(token: str) -> str | None:
    """Return the username a token was issued for, or None if forged or expired."""
    payload, _, sig = token.rpartition(".")
    if not payload or not hmac.compare_digest(sig.encode(), _sign(payload).encode()):
        return None
    # Signature checked first, so the expiry below is one we wrote.
    username, _, exp = payload.rpartition(".")
    return username if username and int(exp) > time.time() else None


if __name__ == "__main__":
    h = hash_password("hunter22")
    assert verify_password("hunter22", h) and not verify_password("hunter23", h)
    t = make_token("a.b")
    assert user_from_token(t) == "a.b"
    assert user_from_token("x" + t) is None
    assert user_from_token("garbage") is None
    assert user_from_token("a.b.ü") is None
    assert user_from_token(make_token("a.b", now=time.time() - TOKEN_TTL - 1)) is None  # expired
    assert user_from_token(t.replace(t.split(".")[2], "9999999999")) is None  # extended expiry
    print("auth ok")
