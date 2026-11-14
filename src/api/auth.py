"""
Password hashing (scrypt) and stateless HMAC-signed login tokens. Stdlib only.
"""

import hashlib
import hmac
import os

from src.core.config import settings

_KEY = settings.SECRET_KEY.encode()


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


# ponytail: tokens never expire; add an issued-at timestamp to the signed payload if that matters.
def make_token(username: str) -> str:
    return f"{username}.{_sign(username)}"


def user_from_token(token: str) -> str | None:
    """Return the username a token was issued for, or None if it is forged."""
    username, _, sig = token.rpartition(".")
    if username and hmac.compare_digest(sig.encode(), _sign(username).encode()):
        return username
    return None


if __name__ == "__main__":
    h = hash_password("hunter22")
    assert verify_password("hunter22", h) and not verify_password("hunter23", h)
    t = make_token("a.b")
    assert user_from_token(t) == "a.b"
    assert user_from_token("x" + t) is None
    assert user_from_token("garbage") is None
    assert user_from_token("a.b.ü") is None
    print("auth ok")
