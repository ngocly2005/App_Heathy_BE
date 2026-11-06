"""Per-user nutrition and water targets, shared by all clients."""
from fastapi import APIRouter
from sqlalchemy import select

from app.calculations import calculate_age, calculate_bmr, calculate_tdee
from app.dependencies import CurrentUser, DbSession
from app.models import HealthProfile, NutritionSettings, User, WaterLog, WaterSettings
from app.schemas import (NutritionSettingsUpsert, WaterAdjustment, WaterAdjustmentResponse,
                         WaterSettingsResponse, WaterSettingsUpsert)

router = APIRouter(tags=["settings"])


def calorie_target(db, user_id):
    custom = db.get(NutritionSettings, user_id)
    if custom and custom.calorie_target is not None:
        return float(custom.calorie_target)
    profile = db.get(HealthProfile, user_id)
    if profile is None:
        return None
    return calculate_tdee(calculate_bmr(float(profile.weight_kg), float(profile.height_cm),
                                      calculate_age(profile.birth_date), profile.sex), profile.activity_level)


def nutrition_response(db, user_id):
    row = db.get(NutritionSettings, user_id)
    values = ({key: getattr(row, key) for key in NutritionSettingsUpsert.model_fields}
              if row else NutritionSettingsUpsert().model_dump())
    effective = calorie_target(db, user_id)
    return {**values, "effective_calorie_target": effective,
            "protein_g": round((effective or 0) * values["protein_pct"] / 100 / 4, 2),
            "carb_g": round((effective or 0) * values["carb_pct"] / 100 / 4, 2),
            "fat_g": round((effective or 0) * values["fat_pct"] / 100 / 9, 2)}


@router.get("/nutrition-settings")
def read_nutrition(current_user: CurrentUser, db: DbSession):
    return nutrition_response(db, current_user.id)


@router.put("/nutrition-settings")
def write_nutrition(payload: NutritionSettingsUpsert, current_user: CurrentUser, db: DbSession):
    db.scalar(select(User).where(User.id == current_user.id).with_for_update())
    row = db.get(NutritionSettings, current_user.id)
    if row is None:
        row = NutritionSettings(user_id=current_user.id)
        db.add(row)
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return nutrition_response(db, current_user.id)


def water_response(db, user_id):
    row = db.get(WaterSettings, user_id)
    target = row.target_ml if row else None
    profile = db.get(HealthProfile, user_id)
    # Same 35 ml/kg base as the Android calculator; settings are shared across devices.
    extra = {"moderate": 300, "very_active": 500, "extra_active": 700}
    automatic = (max(1500, min(4500, round(float(profile.weight_kg) * 35 + extra.get(profile.activity_level, 0))))
                 if profile else 2000)
    return WaterSettingsResponse(target_ml=target, serving_ml=row.serving_ml if row else 200,
                                 effective_target_ml=target if target is not None else automatic)


@router.get("/water-settings", response_model=WaterSettingsResponse)
def read_water(current_user: CurrentUser, db: DbSession):
    return water_response(db, current_user.id)


@router.put("/water-settings", response_model=WaterSettingsResponse)
def write_water(payload: WaterSettingsUpsert, current_user: CurrentUser, db: DbSession):
    db.scalar(select(User).where(User.id == current_user.id).with_for_update())
    row = db.get(WaterSettings, current_user.id)
    if row is None:
        row = WaterSettings(user_id=current_user.id)
        db.add(row)
    row.target_ml, row.serving_ml = payload.target_ml, payload.serving_ml
    db.commit()
    return water_response(db, current_user.id)


@router.post("/water-logs/adjust", response_model=WaterAdjustmentResponse)
def adjust_water(payload: WaterAdjustment, current_user: CurrentUser, db: DbSession):
    db.scalar(select(User).where(User.id == current_user.id).with_for_update())
    logs = list(db.scalars(select(WaterLog).where(WaterLog.user_id == current_user.id,
                       WaterLog.log_date == payload.log_date).order_by(WaterLog.id.desc())))
    total = sum(row.amount_ml for row in logs)
    if payload.amount_ml > 0:
        db.add(WaterLog(user_id=current_user.id, log_date=payload.log_date, amount_ml=payload.amount_ml))
    else:
        remaining = min(-payload.amount_ml, total)
        for row in logs:
            amount = min(remaining, row.amount_ml)
            row.amount_ml -= amount
            remaining -= amount
            if row.amount_ml == 0:
                db.delete(row)
            if remaining == 0:
                break
    db.commit()
    return WaterAdjustmentResponse(date=payload.log_date, total_ml=max(0, total + payload.amount_ml))
