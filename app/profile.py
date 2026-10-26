from datetime import date

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.calculations import calculate_age, calculate_bmi, calculate_bmr, calculate_tdee
from app.dependencies import CurrentUser, DbSession
from app.models import HealthProfile, WeightEntry
from app.schemas import ProfileResponse, ProfileUpsert

router = APIRouter(prefix="/profile", tags=["health profile"])


def build_profile_response(profile: HealthProfile) -> ProfileResponse:
    age = calculate_age(profile.birth_date)
    height_cm = float(profile.height_cm)
    weight_kg = float(profile.weight_kg)
    bmr_kcal = calculate_bmr(weight_kg, height_cm, age, profile.sex)
    return ProfileResponse(
        user_id=profile.user_id,
        birth_date=profile.birth_date,
        age=age,
        sex=profile.sex,
        height_cm=height_cm,
        weight_kg=weight_kg,
        activity_level=profile.activity_level,
        goal=profile.goal,
        bmi=calculate_bmi(weight_kg, height_cm),
        bmr_kcal=bmr_kcal,
        tdee_kcal=calculate_tdee(bmr_kcal, profile.activity_level),
        updated_at=profile.updated_at,
    )


@router.get("", response_model=ProfileResponse)
def read_profile(current_user: CurrentUser, db: DbSession) -> ProfileResponse:
    profile = db.get(HealthProfile, current_user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Health profile not found")
    return build_profile_response(profile)


@router.put("", response_model=ProfileResponse)
def upsert_profile(
    payload: ProfileUpsert,
    current_user: CurrentUser,
    db: DbSession,
) -> ProfileResponse:
    profile = db.get(HealthProfile, current_user.id)
    if profile is None:
        profile = HealthProfile(user_id=current_user.id, **payload.model_dump())
        db.add(profile)
    else:
        for field, value in payload.model_dump().items():
            setattr(profile, field, value)

    today_weight = db.scalar(
        select(WeightEntry).where(
            WeightEntry.user_id == current_user.id,
            WeightEntry.measured_on == date.today(),
        )
    )
    if today_weight is None:
        db.add(
            WeightEntry(
                user_id=current_user.id,
                measured_on=date.today(),
                weight_kg=payload.weight_kg,
            )
        )
    else:
        today_weight.weight_kg = payload.weight_kg

    db.commit()
    db.refresh(profile)
    return build_profile_response(profile)
