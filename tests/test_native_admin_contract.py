"""Shared Android/web Admin contract and live database role enforcement."""
# The shared fixture module sets isolated DB settings before importing app modules.
from test_integration import api, body

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Food, User


def test_database_role_changes_apply_to_existing_access_tokens(api):
    """The DB role, rather than an old token or a client-side label, authorizes Admin."""
    admin_headers = api.user_headers(3)
    body(api.get("/api/v1/admin/users", headers=admin_headers))
    with Session(api.test_engine) as db:
        db.get(User, 3).role = "user"
        db.commit()

    assert body(api.get("/api/v1/auth/me", headers=admin_headers))["role"] == "user"
    for resource in ("users", "foods", "activities", "ai-logs", "analytics"):
        assert api.get(f"/api/v1/admin/{resource}", headers=admin_headers).status_code == 403
    assert api.put("/api/v1/admin/users/2", headers=admin_headers,
                   json={"status": "disabled"}).status_code == 403
    assert api.post("/api/v1/admin/foods", headers=admin_headers, json={
        "name": "Must not be saved", "calories_per_100g": 100,
        "protein_per_100g": 5, "carb_per_100g": 20, "fat_per_100g": 1,
    }).status_code == 403
    assert api.delete("/api/v1/admin/activities/1", headers=admin_headers).status_code == 403
    with Session(api.test_engine) as db:
        assert db.get(User, 2).status == "active"
        assert db.scalar(select(Food).where(Food.name == "Must not be saved")) is None
        db.get(User, 1).role = "admin"
        db.commit()

    # Keep the original user token: a teacher's SQL/bootstrap promotion is visible immediately.
    assert body(api.get("/api/v1/auth/me"))["role"] == "admin"
    assert body(api.get("/api/v1/admin/users"))["total"] == 3


def test_admin_user_status_form_cannot_grant_roles_or_disable_another_admin(api):
    admin_headers = api.user_headers(3)
    assert api.put("/api/v1/admin/users/1", headers=admin_headers,
                   json={"status": "active", "role": "admin"}).status_code == 422
    assert body(api.get("/api/v1/auth/me"))["role"] == "user"
    with Session(api.test_engine) as db:
        db.get(User, 2).role = "admin"
        db.commit()
    assert api.put("/api/v1/admin/users/2", headers=admin_headers,
                   json={"status": "disabled"}).status_code == 409
    with Session(api.test_engine) as db:
        assert db.get(User, 2).status == "active"


def test_admin_catalog_roundtrip_is_shared_with_the_user_food_catalog(api):
    admin_headers = api.user_headers(3)
    initial = {"name": "Native shared food", "calories_per_100g": 120,
               "protein_per_100g": 10, "carb_per_100g": 15,
               "fat_per_100g": 2, "is_active": True}
    created = body(api.post("/api/v1/admin/foods", headers=admin_headers, json=initial), 201)
    item_id = created["id"]
    assert body(api.get(f"/api/v1/admin/foods/{item_id}", headers=admin_headers)) == created
    page = body(api.get("/api/v1/admin/foods", headers=admin_headers,
                        params={"q": "Native shared", "page": 1, "per_page": 1,
                                "sort_field": "name", "sort_order": "DESC"}))
    assert page["total"] == 1 and page["items"] == [created]
    public = body(api.get("/api/v1/foods", params={"q": initial["name"]}))
    assert len(public) == 1 and public[0]["id"] == item_id
    assert public[0]["calories_per_100g"] == 120

    updated = body(api.put(f"/api/v1/admin/foods/{item_id}", headers=admin_headers,
                          json={**initial, "calories_per_100g": 180}))
    assert updated["calories_per_100g"] == 180
    assert body(api.get("/api/v1/foods", params={"q": initial["name"]}))[0]["calories_per_100g"] == 180
    assert api.delete(f"/api/v1/admin/foods/{item_id}", headers=admin_headers).status_code == 204
    assert body(api.get(f"/api/v1/admin/foods/{item_id}", headers=admin_headers))["is_active"] is False
    assert body(api.get("/api/v1/foods", params={"q": initial["name"]})) == []
