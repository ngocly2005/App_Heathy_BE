"""Exercise real HTTP/session/database paths; external Google proof is mocked only."""
from test_integration import api, body, PROFILE

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.google import GoogleIdentity
from app.core.security import verify_password
from app.models import User

PASSWORD = "a strong passphrase 123"


def register(api, email="new@example.com"):
    return body(api.post("/api/v1/auth/register", json={
        "email": email, "full_name": " New Person ", "password": PASSWORD}), 201)


def bearer(tokens):
    return {"Authorization": "Bearer " + tokens["access_token"]}


def test_register_login_refresh_logout_and_profile_for_password_only_user(api):
    tokens = register(api, " New@Example.COM ")
    me = body(api.get("/api/v1/auth/me", headers=bearer(tokens)))
    assert me["email"] == "new@example.com" and me["full_name"] == "New Person"
    assert me["role"] == "user" and me["google_sub"] is None and me["has_password"]
    assert "password" not in me and "password_hash" not in me
    with Session(api.test_engine) as db:
        stored = db.get(User, me["id"])
        assert stored.password_hash.startswith("$argon2id$")
        assert stored.password_hash != PASSWORD and verify_password(PASSWORD, stored.password_hash)
    body(api.put("/api/v1/profile", headers=bearer(tokens), json=PROFILE))
    login = body(api.post("/api/v1/auth/login", json={"email":"NEW@example.com", "password":PASSWORD}))
    assert body(api.get("/api/v1/profile", headers=bearer(login)))["weight_kg"] == 60
    rotated = body(api.post("/api/v1/auth/refresh", json={"refresh_token":login["refresh_token"]}))
    assert api.post("/api/v1/auth/refresh", json={"refresh_token":login["refresh_token"]}).status_code == 401
    body(api.post("/api/v1/auth/logout", json={"refresh_token":rotated["refresh_token"]}))
    assert api.post("/api/v1/auth/refresh", json={"refresh_token":rotated["refresh_token"]}).status_code == 401


def test_duplicate_registration_and_role_injection_do_not_replace_any_account(api):
    register(api)
    assert api.post("/api/v1/auth/register", json={"email":"NEW@example.com", "full_name":"Replace", "password":"changed password"}).status_code == 409
    assert api.post("/api/v1/auth/register", json={"email":"person3@example.com", "full_name":"Replace", "password":PASSWORD}).status_code == 409
    assert api.post("/api/v1/auth/register", json={"email":"other@example.com", "full_name":"Other", "password":PASSWORD, "role":"admin"}).status_code == 422
    with Session(api.test_engine) as db:
        assert db.get(User, 3).role == "admin" and db.get(User, 3).password_hash is None
        assert db.scalar(select(User).where(User.email == "new@example.com")).full_name == "New Person"


def test_wrong_unknown_google_only_and_disabled_password_login_have_same_error(api):
    tokens = register(api)
    invalid = []
    for email in ("new@example.com", "missing@example.com", "person1@example.com"):
        response = api.post("/api/v1/auth/login", json={"email":email, "password":"incorrect"})
        assert response.status_code == 401
        invalid.append(response.json())
    with Session(api.test_engine) as db:
        db.scalar(select(User).where(User.email == "new@example.com")).status = "disabled"
        db.commit()
    response = api.post("/api/v1/auth/login", json={"email":"new@example.com", "password":PASSWORD})
    assert response.status_code == 401 and response.json() == invalid[0] == invalid[1] == invalid[2]
    assert api.get("/api/v1/auth/me", headers=bearer(tokens)).status_code == 401
    assert api.post("/api/v1/auth/refresh", json={"refresh_token":tokens["refresh_token"]}).status_code == 401


def test_validation_hides_credentials_and_does_not_trim_passwords(api):
    for password in ("s3Cr!", "x" * 129):
        response = api.post("/api/v1/auth/register", json={"email":"new@example.com", "full_name":"New", "password":password})
        assert response.status_code == 422 and password not in response.text
        assert "input" not in response.text
    response = api.post("/api/v1/auth/register", json={"email":"new@example.com", "full_name":"  ", "password":PASSWORD})
    assert response.status_code == 422 and PASSWORD not in response.text
    register(api)
    assert api.post("/api/v1/auth/login", json={"email":"new@example.com", "password":" " + PASSWORD}).status_code == 401


def test_link_requires_both_existing_session_and_matching_verified_google(api, monkeypatch):
    tokens = register(api)
    monkeypatch.setattr("app.auth.verify_google_token", lambda _: GoogleIdentity("new-google", "new@example.com", "Google name"))
    # A verified email alone does not merge into an existing password account.
    assert api.post("/api/v1/auth/google", json={"id_token":"g"*30}).status_code == 409
    assert api.post("/api/v1/auth/link-google", headers={"Authorization":""}, json={"id_token":"g"*30}).status_code == 401
    linked = body(api.post("/api/v1/auth/link-google", headers=bearer(tokens), json={"id_token":"g"*30}))
    assert linked["google_sub"] == "new-google" and linked["has_password"]
    google_tokens = body(api.post("/api/v1/auth/google", json={"id_token":"g"*30}))
    me = body(api.get("/api/v1/auth/me", headers=bearer(google_tokens)))
    original = body(api.get("/api/v1/auth/me", headers=bearer(tokens)))
    assert me["id"] == original["id"] and me["full_name"] == "New Person"
    assert body(api.post("/api/v1/auth/login", json={"email":"new@example.com", "password":PASSWORD}))
    monkeypatch.setattr("app.auth.verify_google_token", lambda _: GoogleIdentity("wrong", "other@example.com", "Wrong"))
    assert api.post("/api/v1/auth/link-google", headers=bearer(tokens), json={"id_token":"g"*30}).status_code == 409
    with Session(api.test_engine) as db:
        assert db.get(User, me["id"]).google_sub == "new-google"


def test_google_user_can_add_password_and_change_it_only_with_current_password(api):
    initial = body(api.get("/api/v1/auth/me"))
    assert not initial["has_password"]
    body(api.put("/api/v1/auth/password", json={"new_password":PASSWORD}))
    tokens = body(api.post("/api/v1/auth/login", json={"email":"person1@example.com", "password":PASSWORD}))
    assert body(api.get("/api/v1/auth/me", headers=bearer(tokens)))["id"] == 1
    assert api.put("/api/v1/auth/password", json={"new_password":"different password"}).status_code == 400
    assert api.put("/api/v1/auth/password", json={"current_password":"bad", "new_password":"different password"}).status_code == 400
    body(api.put("/api/v1/auth/password", json={"current_password":PASSWORD, "new_password":"different password"}))
    assert api.post("/api/v1/auth/login", json={"email":"person1@example.com", "password":PASSWORD}).status_code == 401
    body(api.post("/api/v1/auth/login", json={"email":"person1@example.com", "password":"different password"}))
    assert not body(api.get("/api/v1/auth/me", headers=api.user_headers(2)))["has_password"]


def test_password_admin_uses_same_role_protection_and_catalog_as_google_admin(api):
    tokens = register(api)
    headers = bearer(tokens)
    assert api.get("/api/v1/admin/users", headers=headers).status_code == 403
    with Session(api.test_engine) as db:
        user = db.scalar(select(User).where(User.email == "new@example.com"))
        user.role = "admin"
        db.commit()
    assert body(api.get("/api/v1/admin/users", headers=headers))["total"] == 4
    food = body(api.post("/api/v1/admin/foods", headers=headers, json={"name":"Admin food", "calories_per_100g":123,
        "protein_per_100g":3, "carb_per_100g":10, "fat_per_100g":2}), 201)
    assert any(item["id"] == food["id"] for item in body(api.get("/api/v1/foods")))
    with Session(api.test_engine) as db:
        db.scalar(select(User).where(User.email == "new@example.com")).role = "user"
        db.commit()
    assert api.get("/api/v1/admin/users", headers=headers).status_code == 403
