"""HTTP regression checks with isolated in-memory SQLite and mocked providers."""
import io
import os
from datetime import date, timedelta

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
    body(api.post("/api/v1/ai/photo/analyze",params={"date":YESTERDAY},files={"image":("meal.png",photo.getvalue(),"image/png")}))
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
