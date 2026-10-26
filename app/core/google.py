from dataclasses import dataclass

from fastapi import HTTPException
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from pydantic import EmailStr, TypeAdapter, ValidationError

from app.core.config import get_settings


@dataclass(frozen=True)
class GoogleIdentity:
    subject: str
    email: str
    name: str


class GoogleRequest(Request):
    def __call__(self, *args, **kwargs):
        kwargs["timeout"] = 10
        return super().__call__(*args, **kwargs)


def verify_google_token(token: str) -> GoogleIdentity:
    audience = get_settings().google_web_client_id
    if not audience:
        raise HTTPException(status_code=503, detail="Configure GOOGLE_WEB_CLIENT_ID first")

    try:
        claims = id_token.verify_oauth2_token(token, GoogleRequest(), audience)
    except ValueError as error:
        raise HTTPException(status_code=401, detail="Invalid Google ID token") from error
    except GoogleAuthError as error:
        raise HTTPException(status_code=503, detail="Google sign-in unavailable") from error

    subject = claims.get("sub")
    email = claims.get("email")
    if (
        claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}
        or claims.get("email_verified") is not True
        or not isinstance(subject, str)
        or not 0 < len(subject) <= 255
        or not isinstance(email, str)
    ):
        raise HTTPException(status_code=401, detail="Unverified Google identity")
    try:
        verified_email = str(TypeAdapter(EmailStr).validate_python(email)).lower()
    except ValidationError as error:
        raise HTTPException(status_code=401, detail="Invalid Google email") from error

    name = claims.get("name")
    display_name = name.strip() if isinstance(name, str) else ""
    return GoogleIdentity(
        subject=subject,
        email=verified_email,
        name=(display_name or verified_email.split("@", 1)[0])[:120],
    )
