"""Teacher-run: python -m app.admin_setup --email verified-account@example.com"""
import argparse
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models import User


def main():
    parser = argparse.ArgumentParser(description="Grant admin to an existing verified Google account")
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == args.email.strip().lower()))
        if user is None or not user.google_sub or user.status != "active":
            raise SystemExit("Sign in with Google first using an active account; no user was changed.")
        user.role = "admin"
        db.commit()
        print(f"Admin granted to user ID {user.id}. Sign in again in React Admin.")


if __name__ == "__main__":
    main()
