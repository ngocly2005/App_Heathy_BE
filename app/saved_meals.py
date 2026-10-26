from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.calculations import scale_nutrition
from app.dependencies import CurrentUser, DbSession
from app.models import Food, FoodLog, SavedMeal, SavedMealItem, utc_now
from app.schemas import (
    FoodLogResponse,
    SavedMealCreate,
    SavedMealItemCreate,
    SavedMealItemResponse,
    SavedMealLogRequest,
    SavedMealResponse,
    SavedMealUpdate,
)

router = APIRouter(prefix="/saved-meals", tags=["saved meals"])


def get_owned_meal(db: DbSession, user_id: int, meal_id: int) -> SavedMeal:
    meal = db.scalar(
        select(SavedMeal).where(
            SavedMeal.id == meal_id,
            SavedMeal.user_id == user_id,
        )
    )
    if meal is None:
        raise HTTPException(status_code=404, detail="Saved meal not found")
    return meal


def build_items(
    db: DbSession,
    payloads: list[SavedMealItemCreate],
) -> list[SavedMealItem]:
    food_ids = {item.food_id for item in payloads}
    foods = {
        food.id: food
        for food in db.scalars(
            select(Food).where(
                Food.id.in_(food_ids),
                Food.is_active.is_(True),
            )
        )
    }
    if len(foods) != len(food_ids):
        raise HTTPException(status_code=404, detail="One or more foods were not found")

    return [
        SavedMealItem(
            food_id=food.id,
            food_name=food.name,
            grams=item.grams,
            calories_per_100g=food.calories_per_100g,
            protein_per_100g=food.protein_per_100g,
            carb_per_100g=food.carb_per_100g,
            fat_per_100g=food.fat_per_100g,
        )
        for item in payloads
        for food in [foods[item.food_id]]
    ]


def build_response(db: DbSession, meal: SavedMeal) -> SavedMealResponse:
    items = list(
        db.scalars(
            select(SavedMealItem)
            .where(SavedMealItem.saved_meal_id == meal.id)
            .order_by(SavedMealItem.id)
        )
    )
    return SavedMealResponse(
        id=meal.id,
        name=meal.name,
        items=[SavedMealItemResponse.model_validate(item) for item in items],
        created_at=meal.created_at,
        updated_at=meal.updated_at,
    )


@router.post("", response_model=SavedMealResponse, status_code=status.HTTP_201_CREATED)
def create_saved_meal(
    payload: SavedMealCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> SavedMealResponse:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Saved meal name cannot be blank")

    items = build_items(db, payload.items)
    meal = SavedMeal(user_id=current_user.id, name=name)
    db.add(meal)
    try:
        db.flush()
        for item in items:
            item.saved_meal_id = meal.id
            db.add(item)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Saved meal name already exists") from error

    db.refresh(meal)
    return build_response(db, meal)


@router.get("", response_model=list[SavedMealResponse])
def list_saved_meals(
    current_user: CurrentUser,
    db: DbSession,
) -> list[SavedMealResponse]:
    meals = list(
        db.scalars(
            select(SavedMeal)
            .where(SavedMeal.user_id == current_user.id)
            .order_by(SavedMeal.name)
        )
    )
    return [build_response(db, meal) for meal in meals]


@router.get("/{meal_id}", response_model=SavedMealResponse)
def read_saved_meal(
    meal_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> SavedMealResponse:
    return build_response(db, get_owned_meal(db, current_user.id, meal_id))


@router.put("/{meal_id}", response_model=SavedMealResponse)
def update_saved_meal(
    meal_id: int,
    payload: SavedMealUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> SavedMealResponse:
    meal = get_owned_meal(db, current_user.id, meal_id)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="Provide name or items to update")

    if "name" in updates:
        if updates["name"] is None:
            raise HTTPException(status_code=422, detail="Saved meal name cannot be null")
        name = updates["name"].strip()
        if not name:
            raise HTTPException(status_code=422, detail="Saved meal name cannot be blank")
        meal.name = name

    if "items" in updates:
        if payload.items is None:
            raise HTTPException(status_code=422, detail="Saved meal items cannot be null")
        new_items = build_items(db, payload.items)
        db.execute(delete(SavedMealItem).where(SavedMealItem.saved_meal_id == meal.id))
        for item in new_items:
            item.saved_meal_id = meal.id
            db.add(item)

    meal.updated_at = utc_now()

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Saved meal name already exists") from error

    db.refresh(meal)
    return build_response(db, meal)


@router.delete("/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_meal(
    meal_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> Response:
    meal = get_owned_meal(db, current_user.id, meal_id)
    db.delete(meal)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{meal_id}/log", response_model=list[FoodLogResponse])
def log_saved_meal(
    meal_id: int,
    payload: SavedMealLogRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> list[FoodLog]:
    meal = get_owned_meal(db, current_user.id, meal_id)
    items = list(
        db.scalars(
            select(SavedMealItem)
            .where(SavedMealItem.saved_meal_id == meal.id)
            .order_by(SavedMealItem.id)
        )
    )
    food_logs = [
        FoodLog(
            user_id=current_user.id,
            food_id=item.food_id,
            log_date=payload.log_date,
            meal_type=payload.meal_type,
            grams=item.grams,
            food_name=item.food_name,
            calories_kcal=scale_nutrition(
                float(item.calories_per_100g), float(item.grams)
            ),
            protein_g=scale_nutrition(
                float(item.protein_per_100g), float(item.grams)
            ),
            carb_g=scale_nutrition(float(item.carb_per_100g), float(item.grams)),
            fat_g=scale_nutrition(float(item.fat_per_100g), float(item.grams)),
        )
        for item in items
    ]
    db.add_all(food_logs)
    db.commit()
    for food_log in food_logs:
        db.refresh(food_log)
    return food_logs

