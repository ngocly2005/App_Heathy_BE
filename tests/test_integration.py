"""HTTP regression checks with isolated in-memory SQLite and mocked providers."""
import io
import hashlib
import json
import os
from pathlib import Path
from datetime import UTC, date, datetime, timedelta

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "isolated-test-secret-not-for-deployment-20261105"

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models import ActivityType, Food, HealthProfile, User
from app.schemas import MealChatResponse, PhotoAnalysisResponse
from app.core.dates import today as business_today

TODAY = business_today().isoformat()
YESTERDAY = (business_today() - timedelta(days=1)).isoformat()
PROFILE = {"birth_date": "2000-01-15", "sex": "female", "height_cm": 165,
           "weight_kg": 60, "activity_level": "moderate", "goal": "maintain"}


@pytest.fixture
def api():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([User(id=i, email=f"person{i}@example.com", full_name=f"Person {i}",
                        google_sub=f"google-{i}", role="admin" if i == 3 else "user") for i in (1,2,3)])
        db.add(Food(id=1, name="Rice", calories_per_100g=100, protein_per_100g=5, carb_per_100g=20, fat_per_100g=1))
        db.add(ActivityType(id=1, name="Walk", met=3))
        db.commit()
    def session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = session
    with TestClient(app) as client:
        def headers(user=1):
            return {"Authorization": f"Bearer {create_access_token(user)}"}
        client.headers.update(headers())
        client.user_headers = headers
        client.test_engine = engine
        yield client
    app.dependency_overrides.clear()
    engine.dispose()


def body(response, status=200):
    assert response.status_code == status, response.text
    return response.json()


def test_personal_food_crud_logging_and_saved_recipe(api):
    payload = {"name": "Bún bò chay", "calories_per_100g": 115,
               "protein_per_100g": 4, "carb_per_100g": 20, "fat_per_100g": 2}
    created = body(api.post("/api/v1/custom-foods", json=payload), 201)
    assert created["is_custom"] is True and created["has_image"] is False
    food_id = created["id"]
    assert body(api.get("/api/v1/foods", params={"q": "Bún bò chay"}))[0]["id"] == food_id
    assert len(body(api.get("/api/v1/custom-foods"))) == 1
    assert body(api.get("/api/v1/custom-foods", headers=api.user_headers(2))) == []
    assert api.put(f"/api/v1/custom-foods/{food_id}", headers=api.user_headers(2), json=payload).status_code == 404
    assert api.post("/api/v1/food-logs", headers=api.user_headers(2), json={
        "custom_food_id": food_id, "grams": 100, "meal_type": "lunch"}).status_code == 404
    assert api.post("/api/v1/food-logs", json={"food_id": 1, "custom_food_id": food_id,
        "grams": 100, "meal_type": "lunch"}).status_code == 422
    log = body(api.post("/api/v1/food-logs", json={"custom_food_id": food_id,
        "grams": 200, "meal_type": "lunch", "log_date": TODAY}), 201)
    assert log["food_id"] is None and log["calories_kcal"] == 230
    changed = body(api.put(f"/api/v1/custom-foods/{food_id}", json={**payload,
        "name": "Bún bò chay mới", "calories_per_100g": 120}))
    assert changed["name"] == "Bún bò chay mới"
    recipe = body(api.post("/api/v1/saved-meals", json={"name": "Bữa chay", "items": [{
        "food_name": changed["name"], "grams": 200, "calories_per_100g": 120,
        "protein_per_100g": 4, "carb_per_100g": 20, "fat_per_100g": 2}]}), 201)
    assert recipe["items"][0]["food_name"] == "Bún bò chay mới"
    revised = body(api.put(f"/api/v1/saved-meals/{recipe['id']}", json={
        "name": "Bữa chay có cơm", "items": [
            {"food_name": changed["name"], "grams": 150, "calories_per_100g": 120,
             "protein_per_100g": 4, "carb_per_100g": 20, "fat_per_100g": 2},
            {"food_id": 1, "grams": 80}]}))
    assert revised["name"] == "Bữa chay có cơm" and len(revised["items"]) == 2
    assert len(body(api.post(f"/api/v1/saved-meals/{recipe['id']}/log", json={
        "meal_type": "dinner", "log_date": TODAY}))) == 2
    assert api.post("/api/v1/custom-foods", json=payload | {"name": "Bún bò chay mới"}).status_code == 409
    assert api.delete(f"/api/v1/custom-foods/{food_id}").status_code == 204
    assert body(api.get("/api/v1/food-logs", params={"date": TODAY}))[0]["food_name"] == "Bún bò chay"
    assert body(api.get(f"/api/v1/saved-meals/{recipe['id']}"))["items"][0]["food_name"] == "Bún bò chay mới"


def test_food_images_are_local_validated_and_private(api, tmp_path):
    from app.core.config import get_settings
    settings = get_settings()
    old_dir = settings.food_media_dir
    settings.food_media_dir = str(tmp_path)
    try:
        payload = {"name": "Ảnh món riêng", "calories_per_100g": 50,
                   "protein_per_100g": 1, "carb_per_100g": 10, "fat_per_100g": 0}
        personal = body(api.post("/api/v1/custom-foods", json=payload), 201)
        food_id = personal["id"]
        photo = io.BytesIO()
        Image.new("RGB", (12, 8), "red").save(photo, format="PNG")
        image = photo.getvalue()
        assert api.put(f"/api/v1/custom-foods/{food_id}/image", files={
            "image": ("bad.png", b"not a photo", "image/png")}).status_code == 422
        assert api.put(f"/api/v1/custom-foods/{food_id}/image", headers=api.user_headers(2), files={
            "image": ("food.png", image, "image/png")}).status_code == 404
        body(api.put(f"/api/v1/custom-foods/{food_id}/image", files={
            "image": ("food.png", image, "image/png")}))
        served = api.get(f"/api/v1/custom-foods/{food_id}/image")
        assert served.status_code == 200 and served.headers["content-type"] == "image/jpeg"
        assert len(list(tmp_path.glob("*.jpg"))) == 1
        first_file = next(tmp_path.glob("*.jpg"))
        body(api.put(f"/api/v1/custom-foods/{food_id}/image", files={
            "image": ("replacement.png", image, "image/png")}))
        assert not first_file.exists() and len(list(tmp_path.glob("*.jpg"))) == 1
        assert api.get(f"/api/v1/custom-foods/{food_id}/image", headers=api.user_headers(2)).status_code == 404
        assert api.put("/api/v1/admin/foods/1/image", files={"image": ("x.png", image, "image/png")}).status_code == 403
        body(api.put("/api/v1/admin/foods/1/image", headers=api.user_headers(3), files={
            "image": ("x.png", image, "image/png")}))
        assert api.get("/api/v1/foods/1/image").status_code == 200
        assert api.delete(f"/api/v1/custom-foods/{food_id}/image").status_code == 204
        assert api.get(f"/api/v1/custom-foods/{food_id}/image").status_code == 404
        assert len(list(tmp_path.glob("*.jpg"))) == 1  # catalog image remains
    finally:
        settings.food_media_dir = old_dir


def test_bundled_food_catalog_has_100_visible_foods_and_working_photos(api):
    catalog_path = Path(__file__).resolve().parents[1] / "app" / "data" / "food_catalog_100.json"
    photo_dir = catalog_path.parents[1] / "assets" / "food_catalog"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert len(catalog) == len({row["name"] for row in catalog}) == 100
    for row in catalog:
        photo = photo_dir / row["image_filename"]
        assert photo.is_file(), row["name"]
        with Image.open(photo) as image:
            assert image.format == "JPEG" and min(image.size) >= 120
    for name in ("Cooked chicken breast", "Cooked white rice", "Boiled egg", "Banana", "Apple"):
        assert (photo_dir / (hashlib.md5(name.encode()).hexdigest() + ".jpg")).is_file()
    with Session(api.test_engine) as db:
        for index, row in enumerate(catalog, start=2):
            db.add(Food(id=index, name=row["name"], image_filename=row["image_filename"],
                calories_per_100g=row["calories_per_100g"],
                protein_per_100g=row["protein_per_100g"],
                carb_per_100g=row["carb_per_100g"], fat_per_100g=row["fat_per_100g"]))
        db.commit()
    listed = body(api.get("/api/v1/foods"))
    assert len(listed) == 101
    assert sum(food["has_image"] for food in listed) == 100
    response = api.get("/api/v1/foods/2/image")
    assert response.status_code == 200 and response.headers["content-type"] == "image/jpeg"
    assert api.get("/api/v1/foods/2/image", headers={"Authorization": ""}).status_code == 401


def test_activity_history_can_be_reviewed_and_owned(api):
    body(api.put("/api/v1/profile", json=PROFILE))
    log = body(api.post("/api/v1/activity-logs", json={
        "activity_type_id": 1, "duration_minutes": 20, "log_date": YESTERDAY}), 201)
    assert body(api.get("/api/v1/activity-logs"))[0]["id"] == log["id"]
    assert body(api.get("/api/v1/activity-logs", params={"limit": 1, "offset": 1})) == []
    assert body(api.get("/api/v1/activity-logs", params={"date": TODAY})) == []
    assert body(api.get("/api/v1/activity-logs", headers=api.user_headers(2))) == []
    assert api.put(f"/api/v1/activity-logs/{log['id']}", headers=api.user_headers(2),
                   json={"duration_minutes": 30}).status_code == 404
    changed = body(api.put(f"/api/v1/activity-logs/{log['id']}", json={"duration_minutes": 30}))
    assert changed["calories_burned"] > log["calories_burned"]
    assert api.delete(f"/api/v1/activity-logs/{log['id']}").status_code == 204
    assert body(api.get("/api/v1/activity-logs")) == []


def test_manual_activity_is_saved_without_catalog_record(api):
    body(api.put("/api/v1/profile", json=PROFILE))
    payload = {"manual_name": "Đi bộ cầu thang", "manual_met": 4.0,
               "duration_minutes": 30, "log_date": YESTERDAY}
    log = body(api.post("/api/v1/activity-logs", json=payload), 201)
    assert log["activity_type_id"] is None
    assert log["activity_name"] == payload["manual_name"]
    assert log["met_snapshot"] == 4.0
    assert log["calories_burned"] == 126.0
    assert body(api.get("/api/v1/activity-logs", params={"date": YESTERDAY}))[0]["id"] == log["id"]
    for invalid in ({"duration_minutes": 30},
                    {**payload, "activity_type_id": 1},
                    {**payload, "manual_met": None},
                    {**payload, "manual_met": 31},
                    {**payload, "manual_name": " "}):
        assert api.post("/api/v1/activity-logs", json=invalid).status_code == 422


def test_profile_targets_macros_and_validation(api):
    profile = body(api.put("/api/v1/profile", json=PROFILE))
    assert profile["bmi"] == 22.04
    assert body(api.get("/api/v1/dashboard/daily", params={"date": TODAY}))["calorie_target"] == profile["tdee_kcal"]
    settings = {"calorie_target": 2000, "protein_pct": 30, "carb_pct": 40, "fat_pct": 30}
    result = body(api.put("/api/v1/nutrition-settings", json=settings))
    assert result["protein_g"] == 150 and result["fat_g"] == 66.67
    assert body(api.get("/api/v1/dashboard/daily"))["calorie_target"] == 2000
    assert api.put("/api/v1/nutrition-settings", json={**settings, "fat_pct": 10}).status_code == 422
    assert api.put("/api/v1/profile", json={**PROFILE,"birth_date": TODAY}).status_code == 422


def test_food_diary_snapshots_and_ownership(api):
    log = body(api.post("/api/v1/food-logs", json={"food_id": 1, "grams": 150,
                    "meal_type": "lunch", "meal_time": "12:30", "log_date": YESTERDAY}), 201)
    assert log["calories_kcal"] == 150
    admin = api.user_headers(3)
    body(api.put("/api/v1/admin/foods/1", headers=admin, json={"name":"Rice", "calories_per_100g":900,
        "protein_per_100g":10,"carb_per_100g":10,"fat_per_100g":10,"is_active":True}))
    updated = body(api.put(f"/api/v1/food-logs/{log['id']}", json={"grams":300,"meal_type":"dinner","meal_time":"18:00"}))
    assert updated["calories_kcal"] == 300  # The old snapshot survives the catalog edit.
    assert api.put(f"/api/v1/food-logs/{log['id']}", headers=api.user_headers(2),
                   json={"grams":100,"meal_type":"lunch"}).status_code == 404
    detail = body(api.get("/api/v1/history/daily", params={"date":YESTERDAY}))
    assert detail["dashboard"]["calories_consumed"] == 300
    assert body(api.get("/api/v1/history/daily", params={"date":TODAY}))["dashboard"]["food_logs"] == []
    assert api.delete(f"/api/v1/food-logs/{log['id']}").status_code == 204
    assert api.post("/api/v1/food-logs",json={"food_id":1,"grams":0.001,"meal_type":"lunch"}).status_code == 422


def test_activity_and_water_adjustment(api):
    body(api.put("/api/v1/profile", json=PROFILE))
    log = body(api.post("/api/v1/activity-logs", json={"activity_type_id":1,"duration_minutes":30,"log_date":YESTERDAY}),201)
    assert log["calories_burned"] == 94.5
    changed = body(api.put(f"/api/v1/activity-logs/{log['id']}", json={"duration_minutes":60}))
    assert changed["calories_burned"] == 189
    assert body(api.get("/api/v1/water-settings"))["effective_target_ml"] == 2400
    body(api.put("/api/v1/water-settings", json={"target_ml":3000,"serving_ml":500}))
    for delta, expected in ((500,500),(-200,300),(-500,0),(-500,0),(200,200)):
        result = body(api.post("/api/v1/water-logs/adjust",json={"log_date":YESTERDAY,"amount_ml":delta}))
        assert result["total_ml"] == expected
    assert body(api.get("/api/v1/dashboard/daily",params={"date":YESTERDAY}))["water_ml"] == 200
    assert body(api.get("/api/v1/dashboard/daily",params={"date":TODAY}))["water_ml"] == 0


def test_saved_meal_manual_snapshot_and_quick_add(api):
    payload = {"name":"Photo breakfast", "items":[{"food_name":"Soup", "grams":200,
        "calories_per_100g":80,"protein_per_100g":3,"carb_per_100g":10,"fat_per_100g":2}]}
    meal = body(api.post("/api/v1/saved-meals", json=payload),201)
    logs = body(api.post(f"/api/v1/saved-meals/{meal['id']}/log",json={"meal_type":"breakfast","meal_time":"07:30","log_date":YESTERDAY}))
    assert logs[0]["calories_kcal"] == 160 and logs[0]["meal_time"] == "07:30"
    assert api.get(f"/api/v1/saved-meals/{meal['id']}",headers=api.user_headers(2)).status_code == 404
    assert api.post("/api/v1/saved-meals",json=payload).status_code == 409
    assert api.delete(f"/api/v1/saved-meals/{meal['id']}").status_code == 204
    assert len(body(api.get("/api/v1/food-logs",params={"date":YESTERDAY}))) == 1


def test_weight_history_calendar_and_notes(api):
    body(api.put("/api/v1/profile",json=PROFILE))
    body(api.put(f"/api/v1/weight-entries/{YESTERDAY}",json={"weight_kg":65}))
    assert body(api.get("/api/v1/profile"))["weight_kg"] == 60
    body(api.put(f"/api/v1/weight-entries/{TODAY}",json={"weight_kg":59}))
    assert body(api.get("/api/v1/profile"))["weight_kg"] == 59
    body(api.put(f"/api/v1/diary/{YESTERDAY}",json={"content":"A good day","mood":"happy"}))
    calendar = body(api.get("/api/v1/history/calendar",params={"month":YESTERDAY[:7]}))
    day = next(row for row in calendar if row["date"] == YESTERDAY)
    assert day["has_diary"] and day["weight_kg"] == 65
    assert api.delete(f"/api/v1/weight-entries/{TODAY}").status_code == 204
    assert body(api.get("/api/v1/profile"))["weight_kg"] == 65
    assert api.delete(f"/api/v1/weight-entries/{YESTERDAY}").status_code == 409


def test_edit_and_delete_past_weight_preserves_latest_profile_and_other_users(api):
    body(api.put("/api/v1/profile", json=PROFILE))
    older = (business_today() - timedelta(days=40)).isoformat()
    recent = (business_today() - timedelta(days=10)).isoformat()
    body(api.put(f"/api/v1/weight-entries/{older}", json={"weight_kg":65.05}))
    body(api.put(f"/api/v1/weight-entries/{recent}", json={"weight_kg":64.10}))
    body(api.put(f"/api/v1/weight-entries/{TODAY}", json={"weight_kg":59.75}))
    other = api.user_headers(2)
    body(api.put(f"/api/v1/weight-entries/{older}", headers=other, json={"weight_kg":90.05}))

    # Editing a historical record must change that record, not today's/latest measurement.
    changed = body(api.put(f"/api/v1/weight-entries/{older}", json={"weight_kg":63.25}))
    assert changed["measured_on"] == older and changed["weight_kg"] == 63.25
    rows = {row["measured_on"]:row["weight_kg"] for row in body(api.get("/api/v1/weight-entries"))}
    assert rows == {older:63.25, recent:64.10, TODAY:59.75}
    assert body(api.get("/api/v1/profile"))["weight_kg"] == 59.75
    assert body(api.get("/api/v1/weight-entries", headers=other))[0]["weight_kg"] == 90.05

    assert api.delete(f"/api/v1/weight-entries/{older}").status_code == 204
    assert body(api.get("/api/v1/profile"))["weight_kg"] == 59.75
    assert body(api.get("/api/v1/weight-entries", headers=other))[0]["weight_kg"] == 90.05
    assert api.delete(f"/api/v1/weight-entries/{recent}").status_code == 204
    remaining = body(api.get("/api/v1/weight-entries"))
    assert len(remaining) == 1 and remaining[0]["measured_on"] == TODAY
    assert api.delete(f"/api/v1/weight-entries/{TODAY}").status_code == 409
    tomorrow = (business_today() + timedelta(days=1)).isoformat()
    assert api.put(f"/api/v1/weight-entries/{tomorrow}", json={"weight_kg":60}).status_code == 422


def test_weight_date_range_includes_month_boundaries_and_leap_day(api):
    body(api.put("/api/v1/profile", json=PROFILE))
    for day, value in (("2024-01-31",65.0),("2024-02-01",64.5),("2024-02-29",63.25),("2024-03-01",63.0)):
        body(api.put(f"/api/v1/weight-entries/{day}", json={"weight_kg":value}))
    rows = body(api.get("/api/v1/weight-entries", params={"date_from":"2024-02-01","date_to":"2024-02-29"}))
    assert [(row["measured_on"],row["weight_kg"]) for row in rows] == [("2024-02-01",64.5),("2024-02-29",63.25)]
    assert body(api.get("/api/v1/weight-entries", params={"date_from":"2024-04-01","date_to":"2024-04-30"})) == []
    assert body(api.get("/api/v1/profile"))["weight_kg"] == PROFILE["weight_kg"]


def test_dashboard_food_updates_while_burned_calories_exceed_food(api):
    body(api.put("/api/v1/profile", json=PROFILE))
    body(api.put("/api/v1/nutrition-settings", json={"calorie_target":2000,"protein_pct":25,"carb_pct":50,"fat_pct":25}))
    body(api.post("/api/v1/food-logs", json={"food_id":1,"grams":100,"meal_type":"lunch","log_date":YESTERDAY}),201)
    body(api.post("/api/v1/activity-logs", json={"activity_type_id":1,"duration_minutes":120,"log_date":YESTERDAY}),201)
    before = body(api.get("/api/v1/dashboard/daily", params={"date":YESTERDAY}))
    assert before["calories_consumed"] == 100 and before["calories_burned"] == 378
    assert before["net_calories"] == -278 and before["calories_remaining"] == 1900
    body(api.post("/api/v1/food-logs", json={"food_id":1,"grams":50,"meal_type":"snack","log_date":YESTERDAY}),201)
    after = body(api.get("/api/v1/dashboard/daily", params={"date":YESTERDAY}))
    assert after["calories_consumed"] == 150 and after["net_calories"] == -228
    assert after["calories_remaining"] == 1850
    assert body(api.get("/api/v1/dashboard/daily", params={"date":TODAY}))["calories_consumed"] == 0


def test_password_reset_requires_config_and_does_not_reveal_accounts(api, monkeypatch):
    from app.core.config import get_settings
    from app import auth
    from app.models import PasswordResetCode

    settings = get_settings()
    old = (settings.smtp_host, settings.smtp_from_email,
           settings.password_reset_cooldown_seconds)
    messages = []
    try:
        settings.smtp_host = None
        settings.smtp_from_email = None
        assert api.post("/api/v1/auth/password/forgot", json={
            "email": "absent@example.com"}).status_code == 503
        settings.smtp_host = "smtp.example.com"
        settings.smtp_from_email = "fit@example.com"
        settings.password_reset_cooldown_seconds = 0
        monkeypatch.setattr(auth, "send_password_reset_mail",
                            lambda recipient, token, _: messages.append((recipient, token)))
        codes = iter(("00000042", "12345678", "87654321", "11223344"))
        monkeypatch.setattr(auth, "create_password_reset_code", lambda: next(codes))
        registered = body(api.post("/api/v1/auth/register", json={
            "email": "reset@example.com", "full_name": "Reset User", "password": "oldPassword123"}), 201)
        expected = body(api.post("/api/v1/auth/password/forgot", json={
            "email": "RESET@example.com"}), 202)
        assert body(api.post("/api/v1/auth/password/forgot", json={
            "email": "absent@example.com"}), 202) == expected
        assert body(api.post("/api/v1/auth/password/forgot", json={
            "email": "person1@example.com"}), 202) == expected  # Google-only
        assert len(messages) == 1 and messages[0][0] == "reset@example.com"
        token = messages[0][1]
        assert token == "00000042" and len(token) == 8 and token.isascii() and token.isdigit()
        with Session(api.test_engine) as db:
            row = db.get(PasswordResetCode, 4)
            assert row is not None and token not in row.code_hash
        assert api.post("/api/v1/auth/password/reset", json={
            "email": "reset@example.com", "token": registered["access_token"],
            "new_password": "newPassword123"}).status_code == 422
        assert api.post("/api/v1/auth/password/reset", json={
            "email": "absent@example.com", "token": token,
            "new_password": "newPassword123"}).status_code == 400
        body(api.post("/api/v1/auth/password/forgot", json={"email": "reset@example.com"}), 202)
        assert messages[-1][1] == "12345678"
        assert api.post("/api/v1/auth/password/reset", json={
            "email": "reset@example.com", "token": token,
            "new_password": "newPassword123"}).status_code == 400
        token = messages[-1][1]
        for _ in range(3):
            assert api.post("/api/v1/auth/password/reset", json={
                "email": "reset@example.com", "token": "99999999",
                "new_password": "newPassword123"}).status_code == 400
        body(api.post("/api/v1/auth/password/reset", json={
            "email": "reset@example.com", "token": token, "new_password": "newPassword123"}))
        assert api.post("/api/v1/auth/password/reset", json={
            "email": "reset@example.com", "token": token, "new_password": "againPassword123"}).status_code == 400
        assert api.post("/api/v1/auth/login", json={
            "email": "reset@example.com", "password": "oldPassword123"}).status_code == 401
        assert api.post("/api/v1/auth/login", json={
            "email": "reset@example.com", "password": "newPassword123"}).status_code == 200
        assert api.post("/api/v1/auth/refresh", json={
            "refresh_token": registered["refresh_token"]}).status_code == 401
        body(api.post("/api/v1/auth/password/forgot", json={"email": "reset@example.com"}), 202)
        locked_code = messages[-1][1]
        for _ in range(5):
            assert api.post("/api/v1/auth/password/reset", json={
                "email": "reset@example.com", "token": "99999999",
                "new_password": "anotherPassword123"}).status_code == 400
        assert api.post("/api/v1/auth/password/reset", json={
            "email": "reset@example.com", "token": locked_code,
            "new_password": "anotherPassword123"}).status_code == 400
        body(api.post("/api/v1/auth/password/forgot", json={"email": "reset@example.com"}), 202)
        expired_code = messages[-1][1]
        with Session(api.test_engine) as db:
            row = db.get(PasswordResetCode, 4)
            row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            db.commit()
        assert api.post("/api/v1/auth/password/reset", json={
            "email": "reset@example.com", "token": expired_code,
            "new_password": "anotherPassword123"}).status_code == 400
    finally:
        settings.smtp_host, settings.smtp_from_email, settings.password_reset_cooldown_seconds = old


def test_admin_auth_catalog_status_and_analytics(api):
    assert api.get("/api/v1/admin/users").status_code == 403
    admin = api.user_headers(3)
    assert body(api.get("/api/v1/admin/users",headers=admin,params={"q":"person1"}))["total"] == 1
    assert api.put("/api/v1/admin/users/3",headers=admin,json={"status":"disabled"}).status_code == 409
    body(api.put("/api/v1/admin/users/2",headers=admin,json={"status":"disabled"}))
    assert api.get("/api/v1/auth/me",headers=api.user_headers(2)).status_code == 401
    assert api.post("/api/v1/admin/activities",headers=admin,json={"name":"Run","met":-1}).status_code == 422
    assert api.post("/api/v1/admin/activities",headers=admin,json={"name":"Tiny","met":0.001}).status_code == 422
    row = body(api.post("/api/v1/admin/activities",headers=admin,json={"name":"Run","met":8}),201)
    assert api.delete(f"/api/v1/admin/activities/{row['id']}",headers=admin).status_code == 204
    assert all(item["id"] != row["id"] for item in body(api.get("/api/v1/activity-types")))
    assert body(api.get("/api/v1/admin/analytics",headers=admin))["totals"]["total_users"] == 3
    assert api.get("/api/v1/admin/analytics",headers=admin,params={"date_from":TODAY,"date_to":YESTERDAY}).status_code == 422
    from datetime import UTC, datetime
    with Session(api.test_engine) as db:
        db.add(User(id=4,email="timezone@example.com",full_name="Timezone",google_sub="google-4",
                    created_at=datetime(2026,9,15,18,0,tzinfo=UTC)))
        db.commit()
    report = body(api.get("/api/v1/admin/analytics",headers=admin,
                         params={"date_from":"2026-09-16","date_to":"2026-09-16"}))
    assert report["daily"][0]["new_users"] == 1


def test_ai_history_photo_and_errors_are_isolated(api, monkeypatch):
    body(api.put("/api/v1/profile",json=PROFILE))
    seen = []
    def fake_ai(**kwargs):
        seen.append(kwargs)
        if kwargs["response_schema"] is MealChatResponse:
            return MealChatResponse(answer="Try rice", suggestions=["Add vegetables"], disclaimer="Estimate")
        return PhotoAnalysisResponse(items=[],notes="No food",disclaimer="Estimate")
    monkeypatch.setattr("app.ai.ask_groq",fake_ai)
    body(api.post("/api/v1/ai/chat",json={"question":"What to eat?","date":YESTERDAY}))
    assert YESTERDAY in seen[0]["prompt"]
    assert len(body(api.get("/api/v1/ai/chat/history"))) == 1
    assert body(api.get("/api/v1/ai/chat/history",headers=api.user_headers(2))) == []
    photo = io.BytesIO()
    Image.new("RGB",(8,8)).save(photo,format="PNG")
    assert body(api.get("/api/v1/ai/photo/latest", params={"date": YESTERDAY})) is None
    request_id = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
    another_id = "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"
    assert body(api.get("/api/v1/ai/photo/latest", params={"date": YESTERDAY,
        "request_id": request_id})) is None
    body(api.post("/api/v1/ai/photo/analyze",params={"date":YESTERDAY,
        "request_id":request_id},files={"image":("meal.png",photo.getvalue(),"image/png")}))
    latest = body(api.get("/api/v1/ai/photo/latest", params={"date": YESTERDAY}))
    assert latest["id"] > 0 and latest["analysis"]["notes"] == "No food"
    assert latest["request_id"] == request_id
    assert body(api.get("/api/v1/ai/photo/latest", params={"date": YESTERDAY,
        "request_id": request_id}))["id"] == latest["id"]
    assert body(api.get("/api/v1/ai/photo/latest", params={"date": YESTERDAY,
        "request_id": another_id})) is None
    assert body(api.get("/api/v1/ai/photo/latest", params={"date": YESTERDAY},
        headers=api.user_headers(2))) is None
    assert body(api.get("/api/v1/ai/photo/latest", params={"date": YESTERDAY,
        "request_id": request_id}, headers=api.user_headers(2))) is None
    assert body(api.get("/api/v1/food-logs",params={"date":YESTERDAY})) == []
    assert api.post("/api/v1/ai/photo/analyze",files={"image":("x.png",b"not an image","image/png")}).status_code == 422
    confirmed = body(api.post("/api/v1/ai/photo/confirm",json={"log_date":YESTERDAY,"meal_type":"lunch","meal_time":"12:00",
        "items":[{"name":"Edited soup","estimated_grams":250,"calories_kcal":270,"protein_g":12,"carb_g":30,"fat_g":8,"confidence":0.6}]}),201)
    assert confirmed["created_logs"][0]["calories_kcal"] == 270
    assert body(api.get("/api/v1/history/daily",params={"date":YESTERDAY}))["dashboard"]["calories_consumed"] == 270
    def fail(**kwargs):
        raise HTTPException(502,"Provider unavailable")
    monkeypatch.setattr("app.ai.ask_groq",fail)
    assert api.post("/api/v1/ai/chat",json={"question":"Any idea?"}).status_code == 502
    logs = body(api.get("/api/v1/admin/ai-logs",headers=api.user_headers(3)))
    assert logs["total"] == 3 and any(row["status"] == "error" for row in logs["items"])
    assert api.get("/api/v1/admin/ai-logs").status_code == 403
    _assert_groq_sdk_wire(monkeypatch)


def _assert_groq_sdk_wire(monkeypatch):
    """Exercise the real SDK serialization while blocking all external HTTP."""
    import json
    from types import SimpleNamespace
    import httpx
    from pydantic import SecretStr
    import app.core.groq_client as adapter
    real_client=adapter.Groq
    requests=[]
    def handler(request):
        payload=json.loads(request.content)
        requests.append((request.url.path,payload))
        photo=isinstance(payload["messages"][-1]["content"],list)
        content=({"items":[],"notes":"Offline vision","disclaimer":"Estimate"} if photo else
                 {"answer":"Offline chat","suggestions":[],"disclaimer":"Estimate"})
        return httpx.Response(200,json={"id":"offline","object":"chat.completion","created":1,
            "model":payload["model"],"choices":[{"index":0,"finish_reason":"stop",
            "message":{"role":"assistant","content":json.dumps(content)}}]})
    monkeypatch.setattr(adapter,"Groq",lambda **kwargs: real_client(**kwargs,
        http_client=httpx.Client(transport=httpx.MockTransport(handler))))
    monkeypatch.setattr(adapter,"get_settings",lambda:SimpleNamespace(
        groq_api_key=SecretStr("offline-test-key"),groq_model="chat-model",groq_vision_model="vision-model"))
    adapter.ask_groq(system_instruction="Offline",prompt="Photo",response_schema=PhotoAnalysisResponse,
                     image_data=b"offline-image",image_mime_type="image/jpeg")
    adapter.ask_groq(system_instruction="Offline",prompt="Chat",response_schema=MealChatResponse)
    assert requests[0][0] == "/openai/v1/chat/completions"
    assert requests[0][1]["model"] == "vision-model" and "reasoning_format" not in requests[0][1]
    assert requests[1][1]["model"] == "chat-model" and requests[1][1]["reasoning_format"] == "hidden"


def test_google_exchange_refresh_rotation_and_logout(api, monkeypatch):
    from app.core.google import GoogleIdentity
    monkeypatch.setattr("app.auth.verify_google_token",lambda _:GoogleIdentity("google-1","person1@example.com","Person 1"))
    tokens=body(api.post("/api/v1/auth/google",json={"id_token":"mock-google-token-for-tests-only"}))
    me=body(api.get("/api/v1/auth/me",headers={"Authorization":f"Bearer {tokens['access_token']}"}))
    assert me["id"] == 1 and me["role"] == "user"
    rotated=body(api.post("/api/v1/auth/refresh",json={"refresh_token":tokens["refresh_token"]}))
    assert api.post("/api/v1/auth/refresh",json={"refresh_token":tokens["refresh_token"]}).status_code == 401
    body(api.post("/api/v1/auth/logout",json={"refresh_token":rotated["refresh_token"]}))
    assert api.post("/api/v1/auth/refresh",json={"refresh_token":rotated["refresh_token"]}).status_code == 401


def test_business_date_uses_utc_plus_seven(monkeypatch):
    from datetime import UTC, datetime
    class Clock:
        @staticmethod
        def now(zone):
            return datetime(2026,11,5,18,0,tzinfo=UTC).astimezone(zone)
    monkeypatch.setattr("app.core.dates.datetime",Clock)
    assert business_today() == date(2026,11,6)
