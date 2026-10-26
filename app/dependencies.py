from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import TokenError, decode_token
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    db: DbSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized()

    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        user_id = int(str(payload["sub"]))
    except (TokenError, KeyError, TypeError, ValueError) as exc:
        raise unauthorized() from exc

    user = db.get(User, user_id)
    if user is None or user.status != "active" or not user.google_sub:
        raise unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


