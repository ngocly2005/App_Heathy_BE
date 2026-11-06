"""Editable logs preserve the nutrition/MET snapshots recorded originally."""
from datetime import date

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.calculations import calculate_activity_calories
from app.dependencies import CurrentUser, DbSession
from app.models import ActivityLog, ActivityType, FoodLog, HealthProfile, User, WaterLog
from app.schemas import ActivityLogCreate, ActivityLogResponse, FoodLogResponse, FoodLogUpdate, WaterLogResponse

router = APIRouter(tags=["editable logs"])


def owned(db, model, item_id, user_id):
    row = db.scalar(select(model).where(model.id == item_id, model.user_id == user_id).with_for_update())
    if row is None:
        raise HTTPException(404, "Log not found")
    return row


@router.put("/food-logs/{log_id}", response_model=FoodLogResponse)
def update_food(log_id: int, payload: FoodLogUpdate, current_user: CurrentUser, db: DbSession):
    row = owned(db, FoodLog, log_id, current_user.id)
    ratio = payload.grams / float(row.grams)
    for field in ("calories_kcal", "protein_g", "carb_g", "fat_g"):
        setattr(row, field, round(float(getattr(row, field)) * ratio, 2))
    row.grams, row.meal_type, row.meal_time = payload.grams, payload.meal_type, payload.meal_time
    db.commit()
    db.refresh(row)
    return row


class ActivityUpdate(BaseModel):
    duration_minutes: int = Field(gt=0, le=1440)


@router.post("/activity-logs", response_model=ActivityLogResponse, status_code=201)
def create_activity(payload: ActivityLogCreate, current_user: CurrentUser, db: DbSession):
    activity = db.get(ActivityType, payload.activity_type_id)
    if activity is None or not activity.is_active:
        raise HTTPException(404, "Activity type not found")
    profile = db.get(HealthProfile, current_user.id)
    if profile is None:
        raise HTTPException(409, "Create a health profile first")
    row = ActivityLog(user_id=current_user.id, activity_type_id=activity.id,
        log_date=payload.log_date, activity_name=activity.name, met_snapshot=activity.met,
        duration_minutes=payload.duration_minutes,
        calories_burned=calculate_activity_calories(float(activity.met), float(profile.weight_kg), payload.duration_minutes))
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/activity-logs", response_model=list[ActivityLogResponse])
def list_activity(current_user: CurrentUser, db: DbSession, log_date: date = Query(alias="date")):
    return list(db.scalars(select(ActivityLog).where(ActivityLog.user_id == current_user.id,
                           ActivityLog.log_date == log_date).order_by(ActivityLog.id)))


@router.put("/activity-logs/{log_id}", response_model=ActivityLogResponse)
def update_activity(log_id: int, payload: ActivityUpdate, current_user: CurrentUser, db: DbSession):
    row = owned(db, ActivityLog, log_id, current_user.id)
    row.calories_burned = round(float(row.calories_burned) * payload.duration_minutes / row.duration_minutes, 2)
    row.duration_minutes = payload.duration_minutes
    db.commit()
    db.refresh(row)
    return row


@router.delete("/activity-logs/{log_id}", status_code=204)
def delete_activity(log_id: int, current_user: CurrentUser, db: DbSession):
    db.delete(owned(db, ActivityLog, log_id, current_user.id))
    db.commit()
    return Response(status_code=204)


class WaterUpdate(BaseModel):
    amount_ml: int = Field(gt=0, le=5000)


@router.put("/water-logs/{log_id}", response_model=WaterLogResponse)
def update_water(log_id: int, payload: WaterUpdate, current_user: CurrentUser, db: DbSession):
    db.scalar(select(User).where(User.id == current_user.id).with_for_update())
    row = owned(db, WaterLog, log_id, current_user.id)
    row.amount_ml = payload.amount_ml
    db.commit()
    db.refresh(row)
    return row
