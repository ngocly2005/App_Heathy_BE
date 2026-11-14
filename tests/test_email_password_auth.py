"""Exercise real HTTP/session/database paths; external Google proof is mocked only."""
from test_integration import api, body, PROFILE

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.google import GoogleIdentity
from app.core.security import hash_password, verify_password
from app.models import User
import pytest

PASSWORD = "a strong passphrase 123"


@pytest.mark.parametrize("old_password", ["x", " " * 8])
def test_existing_passwords_remain_usable_after_new_password_validation(api, old_password):
    with Session(api.test_engine) as db:
        db.get(User, 1).password_hash = hash_password(old_password)
        db.commit()
    tokens = body(api.post("/api/v1/auth/login", json={"email": "person1@example.com", "password": old_password}))
    body(api.put("/api/v1/auth/password", headers=bearer(tokens), json={"current_password": old_password, "new_password": PASSWORD}))


@pytest.mark.parametrize("email", ["Name+tag@Example.COM", "o'connor@example.com", "a_b-c@example.co.uk", "ngọc@example.com", "a@bücher.de"])
def test_valid_email_forms_are_not_restricted_to_gmail(api, email):
    tokens = body(api.post("/api/v1/auth/register", json={"email": email, "full_name": "Ngọc Lý", "password": PASSWORD}), 201)
    assert body(api.get("/api/v1/auth/me", headers=bearer(tokens)))["role"] == "user"


@pytest.mark.parametrize("field,value", [
    ("email", "thanhthien55200gmail.com"), ("email", "a@@gmail.com"),
    ("email", "a..b@gmail.com"), ("email", "a@-example.com"),
    ("full_name", " \u00a0 "), ("full_name", "x" * 121), ("full_name", "A\nB"),
    ("full_name", "A\u007fB"), ("password", "5500000"), ("password", "x" * 129),
    ("password", " " * 8), ("password", "\u00a0" * 8), ("password", "abcd\nefgh"),
    ("password", "abcd\u0000efgh"), ("password", "abcd\u0085efgh"),
])
def test_registration_rejects_invalid_fields_without_issuing_session(api, field, value):
    payload = {"email": "new@example.com", "full_name": "Ngọc Lý", "password": PASSWORD, field: value}
    response = api.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    assert PASSWORD not in response.text and '"input"' not in response.text
    assert "access_token" not in response.text
    with Session(api.test_engine) as db:
        assert db.scalar(select(User).where(User.email == "new@example.com")) is None


@pytest.mark.parametrize("password,name", [("55000000", "Ngọc Lý"), ("x" * 128, "N" * 120), ("😀" * 128, "😀" * 120), (" 12345678 ", " Name ")])
def test_registration_exact_bounds_unicode_and_password_preservation(api, password, name):
    tokens = body(api.post("/api/v1/auth/register", json={"email": " NEW@Example.COM ", "full_name": name, "password": password}), 201)
    me = body(api.get("/api/v1/auth/me", headers=bearer(tokens)))
    assert me["full_name"] == name.strip() and me["email"] == "new@example.com"
    body(api.post("/api/v1/auth/login", json={"email": me["email"], "password": password}))


@pytest.mark.parametrize("password", [" " * 8, "abcd\nefgh", "x" * 129])
def test_password_update_rejects_invalid_new_secret_and_keeps_existing_login(api, password):
    tokens = register(api)
    response = api.put("/api/v1/auth/password", headers=bearer(tokens), json={"current_password": PASSWORD, "new_password": password})
    assert response.status_code == 422 and '"input"' not in response.text and PASSWORD not in response.text
    body(api.post("/api/v1/auth/login", json={"email": "new@example.com", "password": PASSWORD}))


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


def test_bad_google_link_proof_does_not_look_like_an_expired_app_session(api, monkeypatch):
    tokens = register(api)
    headers = bearer(tokens)

    def invalid_proof(_):
        raise HTTPException(401, "Invalid Google ID token")

    monkeypatch.setattr("app.auth.verify_google_token", invalid_proof)
    # Initial Google login is an auth failure; a failed link is an invalid body proof.
    assert api.post("/api/v1/auth/google", json={"id_token":"g"*30}).status_code == 401
    assert api.post("/api/v1/auth/link-google", headers=headers, json={"id_token":"g"*30}).status_code == 400
    me = body(api.get("/api/v1/auth/me", headers=headers))
    assert me["google_sub"] is None and me["has_password"]
    assert api.post("/api/v1/auth/link-google", headers={"Authorization":""}, json={"id_token":"g"*30}).status_code == 401
