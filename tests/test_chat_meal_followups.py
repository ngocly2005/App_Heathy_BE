"""Chat response/history compatibility without live AI or a live database."""
import json
from datetime import date

import pytest

# Reuse the isolated HTTP fixture, including its test-only environment setup.
from test_integration import api, body, PROFILE, TODAY
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models import AIInteraction
from app.schemas import MealChatResponse


def test_legacy_chat_payload_defaults_followups_without_losing_meal_content():
    meals = [f"Bữa {i}: " + "Chi tiết khẩu phần. " * 80 for i in range(6)]
    legacy = {"answer": "Thực đơn", "suggestions": meals, "disclaimer": "Ước tính"}
    result = MealChatResponse.model_validate(legacy)
    assert result.suggestions == meals
    assert result.follow_up_questions == []
    assert len(result.suggestions[-1]) > 1000


def test_followup_schema_rejects_meal_sized_prompts():
    payload = {"answer": "Thực đơn", "suggestions": ["Bữa trưa đầy đủ"], "disclaimer": "Ước tính"}
    with pytest.raises(ValidationError):
        MealChatResponse.model_validate({**payload, "follow_up_questions": ["x" * 121]})
    with pytest.raises(ValidationError):
        MealChatResponse.model_validate({**payload, "follow_up_questions": ["Hỏi tiếp?"] * 5})


def test_chat_saves_full_meals_and_separate_followups_in_paginated_history(api, monkeypatch):
    body(api.put("/api/v1/profile", json=PROFILE))
    meals = [f"Bữa {i}: " + "Món ăn và khẩu phần chi tiết. " * 45 for i in range(6)]
    followups = ["Chi tiết bữa trưa", "Đổi sang món chay"]
    seen = []

    def fake_ai(**kwargs):
        seen.append(kwargs)
        return MealChatResponse(answer="Tham khảo các bữa dưới đây", suggestions=meals,
                                disclaimer="Ước tính", follow_up_questions=followups)

    monkeypatch.setattr("app.ai.ask_groq", fake_ai)
    first = body(api.post("/api/v1/ai/chat", json={"question": "Gợi ý thực đơn", "date": TODAY}))
    assert first["suggestions"] == meals and first["follow_up_questions"] == followups
    body(api.post("/api/v1/ai/chat", json={"question": "Chi tiết bữa trưa", "date": TODAY}))
    history_context = json.loads(seen[-1]["prompt"])["history"]
    assert history_context[-1]["suggestions"] == meals
    assert "follow_up_questions" in seen[0]["system_instruction"]
    assert "Never put a meal description" in seen[0]["system_instruction"]
    latest = body(api.get("/api/v1/ai/chat/history", params={"limit": 1}))
    older = body(api.get("/api/v1/ai/chat/history", params={"before_id": latest[0]["id"], "limit": 1}))
    assert len(older) == 1 and older[0]["id"] < latest[0]["id"]
    assert older[0]["response"]["suggestions"] == meals
    assert older[0]["response"]["follow_up_questions"] == followups
    assert body(api.get("/api/v1/ai/chat/history", headers=api.user_headers(2))) == []
    assert body(api.get("/api/v1/food-logs", params={"date": TODAY})) == []


def test_followup_context_includes_meals_from_legacy_stored_response(api, monkeypatch):
    body(api.put("/api/v1/profile", json=PROFILE))
    legacy = {"answer": "Đây là thực đơn", "suggestions": ["Bữa trưa: 150 g gà và 100 g cơm"], "disclaimer": "Ước tính"}
    with Session(api.test_engine) as db:
        record = AIInteraction(user_id=1, kind="chat", context_date=date.fromisoformat(TODAY),
                               question="Gợi ý bữa ăn", response=legacy, status="success")
        db.add(record)
        db.commit()
    seen = []

    def fake_ai(**kwargs):
        seen.append(json.loads(kwargs["prompt"]))
        return MealChatResponse(answer="Chi tiết khẩu phần", suggestions=[], disclaimer="Ước tính",
                                follow_up_questions=["Đổi sang món chay"])

    monkeypatch.setattr("app.ai.ask_groq", fake_ai)
    body(api.post("/api/v1/ai/chat", json={"question": "Chi tiết bữa trưa", "date": TODAY}))
    assert seen[0]["history"][0]["suggestions"] == legacy["suggestions"]
    history = body(api.get("/api/v1/ai/chat/history"))
    assert history[0]["response"] == legacy
    assert history[1]["response"]["follow_up_questions"] == ["Đổi sang món chay"]
