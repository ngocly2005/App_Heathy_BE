"""Private reusable food recipes owned by one account."""

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.dependencies import CurrentUser, DbSession
from app.models import UserFood
from app.schemas import FoodResponse, UserFoodInput
from app.food_media import remove_image

router = APIRouter(prefix="/custom-foods", tags=["personal foods"])


def owned(db: DbSession, user_id: int, food_id: int) -> UserFood:
    row = db.scalar(select(UserFood).where(UserFood.id == food_id, UserFood.user_id == user_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Personal food not found")
    return row


def commit(db: DbSession):
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Personal food name already exists") from error


@router.get("", response_model=list[FoodResponse])
def list_custom_foods(current_user: CurrentUser, db: DbSession):
    return list(db.scalars(select(UserFood).where(UserFood.user_id == current_user.id).order_by(UserFood.name)))


@router.post("", response_model=FoodResponse, status_code=status.HTTP_201_CREATED)
def create_custom_food(payload: UserFoodInput, current_user: CurrentUser, db: DbSession):
    row = UserFood(user_id=current_user.id, **payload.model_dump())
    db.add(row)
    commit(db)
    db.refresh(row)
    return row


@router.put("/{food_id}", response_model=FoodResponse)
def update_custom_food(food_id: int, payload: UserFoodInput, current_user: CurrentUser, db: DbSession):
    row = owned(db, current_user.id, food_id)
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    commit(db)
    db.refresh(row)
    return row


@router.delete("/{food_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_custom_food(food_id: int, current_user: CurrentUser, db: DbSession):
    row = owned(db, current_user.id, food_id)
    filename = row.image_filename
    db.delete(row)
    db.commit()
    if filename:
        remove_image(filename)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
