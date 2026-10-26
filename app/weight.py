from datetime import date

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, select

from app.dependencies import CurrentUser, DbSession
from app.models import HealthProfile, WeightEntry
from app.schemas import WeightEntryResponse, WeightEntryUpsert

router = APIRouter(prefix="/weight-entries", tags=["weight"])


@router.get("", response_model=list[WeightEntryResponse])
def list_weight_entries(
    current_user: CurrentUser,
    db: DbSession,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> list[WeightEntry]:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must not be after date_to")

    statement = select(WeightEntry).where(WeightEntry.user_id == current_user.id)
    if date_from is not None:
        statement = statement.where(WeightEntry.measured_on >= date_from)
    if date_to is not None:
        statement = statement.where(WeightEntry.measured_on <= date_to)

    return list(db.scalars(statement.order_by(WeightEntry.measured_on)))


@router.put("/{measured_on}", response_model=WeightEntryResponse)
def upsert_weight_entry(
    measured_on: date,
    payload: WeightEntryUpsert,
    current_user: CurrentUser,
    db: DbSession,
) -> WeightEntry:
    entry = db.scalar(
        select(WeightEntry).where(
            WeightEntry.user_id == current_user.id,
            WeightEntry.measured_on == measured_on,
        )
    )
    if entry is None:
        entry = WeightEntry(
            user_id=current_user.id,
            measured_on=measured_on,
            weight_kg=payload.weight_kg,
        )
        db.add(entry)
    else:
        entry.weight_kg = payload.weight_kg

    if measured_on == date.today():
        profile = db.get(HealthProfile, current_user.id)
        if profile is not None:
            profile.weight_kg = payload.weight_kg

    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{measured_on}", status_code=status.HTTP_204_NO_CONTENT)
def delete_weight_entry(
    measured_on: date,
    current_user: CurrentUser,
    db: DbSession,
) -> Response:
    entry = db.scalar(
        select(WeightEntry).where(
            WeightEntry.user_id == current_user.id,
            WeightEntry.measured_on == measured_on,
        )
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Weight entry not found")

    profile = db.get(HealthProfile, current_user.id)
    entry_count = db.scalar(
        select(func.count()).select_from(WeightEntry).where(
            WeightEntry.user_id == current_user.id
        )
    )
    if profile is not None and entry_count == 1:
        raise HTTPException(
            status_code=409,
            detail="A health profile must keep at least one weight entry",
        )

    db.delete(entry)
    db.flush()
    latest = db.scalar(
        select(WeightEntry)
        .where(WeightEntry.user_id == current_user.id)
        .order_by(WeightEntry.measured_on.desc())
        .limit(1)
    )
    if profile is not None and latest is not None:
        profile.weight_kg = latest.weight_kg

    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

