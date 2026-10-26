from datetime import date

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select

from app.dependencies import CurrentUser, DbSession
from app.models import DiaryEntry, WaterLog, WeightEntry
from app.schemas import (
    DiaryResponse,
    DiaryUpsert,
    HistoryDetailResponse,
    WaterLogResponse,
    WeightEntryResponse,
)
from app.tracking import daily_dashboard

router = APIRouter(tags=["diary and history"])


def find_diary(db: DbSession, user_id: int, entry_date: date) -> DiaryEntry | None:
    return db.scalar(
        select(DiaryEntry).where(
            DiaryEntry.user_id == user_id,
            DiaryEntry.entry_date == entry_date,
        )
    )


@router.get("/diary/{entry_date}", response_model=DiaryResponse)
def read_diary(
    entry_date: date,
    current_user: CurrentUser,
    db: DbSession,
) -> DiaryEntry:
    entry = find_diary(db, current_user.id, entry_date)
    if entry is None:
        raise HTTPException(status_code=404, detail="Diary entry not found")
    return entry


@router.put("/diary/{entry_date}", response_model=DiaryResponse)
def upsert_diary(
    entry_date: date,
    payload: DiaryUpsert,
    current_user: CurrentUser,
    db: DbSession,
) -> DiaryEntry:
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Diary content cannot be blank")

    entry = find_diary(db, current_user.id, entry_date)
    if entry is None:
        entry = DiaryEntry(
            user_id=current_user.id,
            entry_date=entry_date,
            content=content,
            mood=payload.mood,
        )
        db.add(entry)
    else:
        entry.content = content
        entry.mood = payload.mood

    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/diary/{entry_date}", status_code=status.HTTP_204_NO_CONTENT)
def delete_diary(
    entry_date: date,
    current_user: CurrentUser,
    db: DbSession,
) -> Response:
    entry = find_diary(db, current_user.id, entry_date)
    if entry is None:
        raise HTTPException(status_code=404, detail="Diary entry not found")
    db.delete(entry)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/history/daily", response_model=HistoryDetailResponse)
def history_daily(
    current_user: CurrentUser,
    db: DbSession,
    selected_date: date = Query(alias="date"),
) -> HistoryDetailResponse:
    dashboard = daily_dashboard(current_user, db, selected_date)
    water_logs = list(
        db.scalars(
            select(WaterLog)
            .where(
                WaterLog.user_id == current_user.id,
                WaterLog.log_date == selected_date,
            )
            .order_by(WaterLog.created_at, WaterLog.id)
        )
    )
    weight = db.scalar(
        select(WeightEntry).where(
            WeightEntry.user_id == current_user.id,
            WeightEntry.measured_on == selected_date,
        )
    )
    diary = find_diary(db, current_user.id, selected_date)

    return HistoryDetailResponse(
        date=selected_date,
        dashboard=dashboard,
        water_logs=[WaterLogResponse.model_validate(item) for item in water_logs],
        weight=(
            WeightEntryResponse.model_validate(weight) if weight is not None else None
        ),
        diary=DiaryResponse.model_validate(diary) if diary is not None else None,
    )

