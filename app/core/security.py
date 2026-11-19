from datetime import UTC, datetime, timedelta
from hashlib import sha256
import hmac
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from jwt import InvalidTokenError

from app.core.config import get_settings

settings = get_settings()
password_hasher = PasswordHasher()
# Verify an Argon2 hash even when an email has no password account.
_dummy_password_hash = password_hasher.hash(str(uuid4()))


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, encoded: str | None) -> bool:
    try:
        valid = password_hasher.verify(encoded or _dummy_password_hash, password)
        return bool(encoded) and valid
    except (InvalidHashError, VerificationError):
        return False


class TokenError(ValueError):
    pass


def create_token(
    user_id: int,
    token_type: str,
    expires_delta: timedelta,
    password_fingerprint: str | None = None,
) -> tuple[str, str, datetime]:
    now = datetime.now(UTC)
    expires_at = now + expires_delta
    jti = str(uuid4())
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": expires_at,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    if password_fingerprint is not None:
        payload["pwd"] = password_fingerprint
    token = jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return token, jti, expires_at


def create_access_token(user_id: int) -> str:
    token, _, _ = create_token(
        user_id=user_id,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_minutes),
    )
    return token


def create_refresh_token(user_id: int) -> tuple[str, str, datetime]:
    return create_token(
        user_id=user_id,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_days),
    )


def reset_password_fingerprint(password_hash: str) -> str:
    """Bind a reset token to the current hash without exposing that hash."""
    return hmac.new(settings.secret_key.encode(), password_hash.encode(), sha256).hexdigest()


def create_password_reset_token(user_id: int, password_hash: str) -> str:
    token, _, _ = create_token(
        user_id=user_id,
        token_type="password_reset",
        expires_delta=timedelta(minutes=settings.password_reset_minutes),
        password_fingerprint=reset_password_fingerprint(password_hash),
    )
    return token


def decode_token(token: str, expected_type: str) -> dict[str, object]:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["sub", "type", "jti", "iat", "exp"]},
        )
    except InvalidTokenError as exc:
        raise TokenError("Invalid or expired token") from exc

    if payload.get("type") != expected_type:
        raise TokenError("Incorrect token type")
    return payload
