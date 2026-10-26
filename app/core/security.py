from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from jwt import InvalidTokenError

from app.core.config import get_settings

settings = get_settings()


class TokenError(ValueError):
    pass


def create_token(
    user_id: int,
    token_type: str,
    expires_delta: timedelta,
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
