from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.google import verify_google_token
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.dependencies import CurrentUser, DbSession
from app.models import RefreshToken, User
from app.schemas import (
    GoogleLoginRequest,
    MessageResponse,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


def create_token_pair(db: DbSession, user_id: int) -> TokenResponse:
    access_token = create_access_token(user_id)
    refresh_token, refresh_jti, refresh_expires_at = create_refresh_token(user_id)
    db.add(
        RefreshToken(
            user_id=user_id,
            jti=refresh_jti,
            expires_at=refresh_expires_at,
        )
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/google", response_model=TokenResponse)
def google_login(payload: GoogleLoginRequest, db: DbSession) -> TokenResponse:
    identity = verify_google_token(payload.id_token)
    user = db.scalar(select(User).where(User.google_sub == identity.subject))
    if user is None:
        if db.scalar(select(User.id).where(User.email == identity.email)) is not None:
            raise HTTPException(
                status_code=409,
                detail="Account identity conflict; complete migration with Lesson 17",
            )
        user = User(
            google_sub=identity.subject,
            email=identity.email,
            full_name=identity.name,
        )
        db.add(user)
    elif user.status != "active":
        raise HTTPException(status_code=401, detail="Account is disabled")

    try:
        db.flush()
        tokens = create_token_pair(db, user.id)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Google account conflict") from error
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: DbSession) -> TokenResponse:
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
        user_id = int(str(claims["sub"]))
        jti = str(claims["jti"])
    except (TokenError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from exc

    stored_token = db.scalar(
        select(RefreshToken).where(RefreshToken.jti == jti).with_for_update()
    )
    now = datetime.now(UTC)
    expires_at = stored_token.expires_at if stored_token is not None else now
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if (
        stored_token is None
        or stored_token.revoked_at is not None
        or expires_at <= now
        or stored_token.user_id != user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = db.get(User, user_id)
    if user is None or user.status != "active" or not user.google_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    stored_token.revoked_at = now
    token_pair = create_token_pair(db, user.id)
    db.commit()
    return token_pair


@router.post("/logout", response_model=MessageResponse)
def logout(payload: RefreshRequest, db: DbSession) -> MessageResponse:
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
        stored_token = db.scalar(
            select(RefreshToken).where(RefreshToken.jti == str(claims["jti"]))
        )
    except (TokenError, KeyError):
        stored_token = None

    if stored_token is not None and stored_token.revoked_at is None:
        stored_token.revoked_at = datetime.now(UTC)
        db.commit()
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserResponse)
def read_me(current_user: CurrentUser) -> User:
    return current_user
