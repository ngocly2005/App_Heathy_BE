from datetime import UTC, datetime
from hashlib import sha256
import hmac
import logging
from threading import Lock
from time import monotonic

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.core.google import verify_google_token
from app.core.config import get_settings
from app.core.mail import reset_mail_configured, send_password_reset_mail
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    create_password_reset_token,
    decode_token,
    hash_password,
    password_hasher,
    reset_password_fingerprint,
    verify_password,
)
from app.dependencies import CurrentUser, DbSession
from app.models import RefreshToken, User
from app.schemas import (
    GoogleLoginRequest,
    EmailLoginRequest,
    RegisterRequest,
    PasswordUpdateRequest,
    PasswordResetStartRequest,
    PasswordResetFinishRequest,
    MessageResponse,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = logging.getLogger(__name__)
_reset_cooldown: dict[str, float] = {}
_reset_cooldown_lock = Lock()


def _allow_reset_request(email: str, seconds: int) -> bool:
    if seconds <= 0:
        return True
    key = sha256(email.encode()).hexdigest()
    now = monotonic()
    with _reset_cooldown_lock:
        if len(_reset_cooldown) > 4096:
            _reset_cooldown.clear()
        if _reset_cooldown.get(key, 0) > now:
            return False
        _reset_cooldown[key] = now + seconds
        return True


def _deliver_reset_code(recipient: str, token: str) -> None:
    try:
        send_password_reset_mail(recipient, token, get_settings())
    except Exception as error:
        # Never log the token or recipient; the public response is identical.
        logger.warning("Password reset email delivery failed (%s)", type(error).__name__)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: DbSession) -> TokenResponse:
    if db.scalar(select(User.id).where(User.email == str(payload.email))) is not None:
        raise HTTPException(409, "Email already registered; sign in using your existing method")
    user = User(email=str(payload.email), full_name=payload.full_name,
                password_hash=hash_password(payload.password.get_secret_value()))
    db.add(user)
    try:
        db.flush()
        tokens = create_token_pair(db, user.id)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, "Email already registered; sign in using your existing method") from error
    return tokens


@router.post("/login", response_model=TokenResponse)
def login(payload: EmailLoginRequest, db: DbSession) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == str(payload.email)))
    password = payload.password.get_secret_value()
    valid = verify_password(password, user.password_hash if user else None)
    if not valid or user is None or user.status != "active":
        raise HTTPException(401, "Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    if password_hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    tokens = create_token_pair(db, user.id)
    db.commit()
    return tokens


@router.put("/password", response_model=MessageResponse)
def update_password(payload: PasswordUpdateRequest, current_user: CurrentUser, db: DbSession):
    user = db.scalar(select(User).where(User.id == current_user.id).with_for_update().execution_options(populate_existing=True))
    if user is None or user.status != "active":
        raise HTTPException(401, "Account is disabled")
    if user.password_hash and (payload.current_password is None or not verify_password(
            payload.current_password.get_secret_value(), user.password_hash)):
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = hash_password(payload.new_password.get_secret_value())
    db.commit()
    return MessageResponse(message="Password updated")


@router.post("/password/forgot", response_model=MessageResponse, status_code=202)
def forgot_password(payload: PasswordResetStartRequest, background_tasks: BackgroundTasks,
                    db: DbSession) -> MessageResponse:
    settings = get_settings()
    if not reset_mail_configured(settings):
        # Independent of account existence, and honest about missing delivery.
        raise HTTPException(503, "Password reset email is not configured")
    email = str(payload.email)
    if _allow_reset_request(email, settings.password_reset_cooldown_seconds):
        user = db.scalar(select(User).where(User.email == email))
        if user is not None and user.status == "active" and user.password_hash:
            token = create_password_reset_token(user.id, user.password_hash)
            background_tasks.add_task(_deliver_reset_code, email, token)
    return MessageResponse(message="If this email has a password account, a reset code will be sent")


@router.post("/password/reset", response_model=MessageResponse)
def reset_password(payload: PasswordResetFinishRequest, db: DbSession) -> MessageResponse:
    invalid = HTTPException(400, "Invalid or expired reset code")
    try:
        claims = decode_token(payload.token, expected_type="password_reset")
        user_id = int(str(claims["sub"]))
        fingerprint = str(claims["pwd"])
    except (TokenError, KeyError, TypeError, ValueError) as error:
        raise invalid from error
    user = db.scalar(select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True))
    if (user is None or user.status != "active" or not user.password_hash or
            not hmac.compare_digest(fingerprint, reset_password_fingerprint(user.password_hash))):
        raise invalid
    user.password_hash = hash_password(payload.new_password.get_secret_value())
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id,
        RefreshToken.revoked_at.is_(None)).values(revoked_at=datetime.now(UTC)))
    db.commit()
    return MessageResponse(message="Password reset; sign in with the new password")


@router.post("/link-google", response_model=UserResponse)
def link_google(payload: GoogleLoginRequest, current_user: CurrentUser, db: DbSession):
    try:
        identity = verify_google_token(payload.id_token)
    except HTTPException as error:
        if error.status_code == 401:
            # The app bearer is valid; it is the supplied Google proof that failed.
            # A 401 here would make clients rotate/clear a perfectly valid session.
            raise HTTPException(400, "Invalid Google proof; check Google configuration and try linking again") from error
        raise
    user = db.scalar(select(User).where(User.id == current_user.id).with_for_update().execution_options(populate_existing=True))
    if user is None or user.status != "active":
        raise HTTPException(401, "Account is disabled")
    if identity.email != user.email:
        raise HTTPException(409, "Choose the Google account with the same email as your current account")
    if user.google_sub and user.google_sub != identity.subject:
        raise HTTPException(409, "This account is already linked to a different Google identity")
    user.google_sub = identity.subject
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, "Google account is already linked") from error
    return user


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
                detail="Email already registered; sign in with your password, then link Google in Account security",
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
    if user is None or user.status != "active" or not (user.google_sub or user.password_hash):
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
