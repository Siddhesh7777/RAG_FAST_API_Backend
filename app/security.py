import base64
import hashlib
import hmac
import os
import time

import jwt  # the PyJWT library

from app.config import settings

ALGORITHM = "HS256"  # signing method: one shared secret signs and checks
TOKEN_MINUTES = 60  # a token stops working after an hour

# scrypt cost settings. Higher numbers make guessing passwords slower for attackers.
_SCRYPT = {"n": 2**14, "r": 8, "p": 1}


def hash_password(password: str) -> str:
    salt = os.urandom(16)  # 16 random bytes, different for every user
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, **_SCRYPT)
    # Stored as "scrypt$<salt>$<hash>" so we can verify it later.
    return "scrypt${}${}".format(
        base64.b64encode(salt).decode(), base64.b64encode(digest).decode()
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_b64, digest_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
    except ValueError:
        return False  # a malformed stored value means "no match", not a crash

    # Scramble the typed password with the SAME salt, then compare.
    candidate = hashlib.scrypt(password.encode("utf-8"), salt=salt, **_SCRYPT)
    # compare_digest takes the same time however many characters match, so an
    # attacker can't learn the hash from timing.
    return hmac.compare_digest(candidate, expected)


def create_token(username: str, minutes: int = TOKEN_MINUTES) -> str:
    now = int(time.time())
    # sub = subject (who), iat = issued at, exp = expires at.
    payload = {"sub": username, "iat": now, "exp": now + minutes * 60}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> str:
    # algorithms=[...] is essential: it stops attackers sending a token that
    # claims "no signature needed". Expiry is checked automatically.
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    username = payload.get("sub")
    if not username:
        raise jwt.InvalidTokenError("missing subject")
    return username
