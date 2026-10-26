from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    status: str
    google_sub: str
    created_at: datetime

class MealChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    question: str = Field(min_length=2, max_length=1000)


class MealChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    suggestions: list[str]
    disclaimer: str

class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=20, max_length=10000)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class MessageResponse(BaseModel):
    message: str


Sex = Literal["male", "female"]
ActivityLevel = Literal["sedentary", "light", "moderate", "very_active"]
HealthGoal = Literal["lose", "maintain", "gain"]


class ProfileUpsert(BaseModel):
    birth_date: date
    sex: Sex
    height_cm: float = Field(gt=80, le=250)
    weight_kg: float = Field(gt=20, le=400)
    activity_level: ActivityLevel
    goal: HealthGoal = "maintain"

    @field_validator("birth_date")
    @classmethod
    def birth_date_must_be_in_the_past(cls, birth_date: date) -> date:
        if birth_date >= date.today():
            raise ValueError("Birth date must be in the past")
        return birth_date


class ProfileResponse(BaseModel):
    user_id: int
    birth_date: date
    age: int
    sex: str
    height_cm: float
    weight_kg: float
    activity_level: str
    goal: str
    bmi: float
    bmr_kcal: float
    tdee_kcal: float
    updated_at: datetime


MealType = Literal["breakfast", "lunch", "dinner", "snack"]


class FoodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    calories_per_100g: float
    protein_per_100g: float
    carb_per_100g: float
    fat_per_100g: float


class FoodLogCreate(BaseModel):
    food_id: int
    grams: float = Field(gt=0, le=10000)
    meal_type: MealType
    log_date: date = Field(default_factory=date.today)


class FoodLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    food_id: int | None
    log_date: date
    meal_type: str
    grams: float
    food_name: str
    calories_kcal: float
    protein_g: float
    carb_g: float
    fat_g: float
    created_at: datetime


class WaterLogCreate(BaseModel):
    amount_ml: int = Field(gt=0, le=5000)
    log_date: date = Field(default_factory=date.today)


class WaterLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    log_date: date
    amount_ml: int
    created_at: datetime


class ActivityTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    met: float
    is_active: bool


class ActivityLogCreate(BaseModel):
    activity_type_id: int
    duration_minutes: int = Field(gt=0, le=1440)
    log_date: date = Field(default_factory=date.today)


class ActivityLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activity_type_id: int | None
    log_date: date
    duration_minutes: int
    activity_name: str
    met_snapshot: float
    calories_burned: float
    created_at: datetime


class MacroSummary(BaseModel):
    protein_g: float
    carb_g: float
    fat_g: float
    protein_pct: float
    carb_pct: float
    fat_pct: float


class DailyDashboardResponse(BaseModel):
    date: date
    calories_consumed: float
    calories_burned: float
    net_calories: float
    calorie_target: float | None
    calories_remaining: float | None
    water_ml: int
    macros: MacroSummary
    food_logs: list[FoodLogResponse]
    activity_logs: list[ActivityLogResponse]


HistoryStatus = Literal[
    "under",
    "on_target",
    "over",
    "no_target",
    "logged",
    "no_data",
]


class HistoryDayResponse(BaseModel):
    date: date
    calories_consumed: float
    calories_burned: float
    water_ml: int
    calorie_target: float | None
    weight_kg: float | None
    has_diary: bool
    status: HistoryStatus


class WeightEntryUpsert(BaseModel):
    weight_kg: float = Field(gt=20, le=400)


class WeightEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    measured_on: date
    weight_kg: float
    created_at: datetime


class DiaryUpsert(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    mood: str | None = Field(default=None, min_length=1, max_length=30)


class DiaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entry_date: date
    content: str
    mood: str | None
    created_at: datetime
    updated_at: datetime


class HistoryDetailResponse(BaseModel):
    date: date
    dashboard: DailyDashboardResponse
    water_logs: list[WaterLogResponse]
    weight: WeightEntryResponse | None
    diary: DiaryResponse | None


class SavedMealItemCreate(BaseModel):
    food_id: int
    grams: float = Field(gt=0, le=10000)


class SavedMealCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    items: list[SavedMealItemCreate] = Field(min_length=1, max_length=30)


class SavedMealUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    items: list[SavedMealItemCreate] | None = Field(
        default=None,
        min_length=1,
        max_length=30,
    )


class SavedMealItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    food_id: int | None
    food_name: str
    grams: float
    calories_per_100g: float
    protein_per_100g: float
    carb_per_100g: float
    fat_per_100g: float


class SavedMealResponse(BaseModel):
    id: int
    name: str
    items: list[SavedMealItemResponse]
    created_at: datetime
    updated_at: datetime


class SavedMealLogRequest(BaseModel):
    meal_type: MealType
    log_date: date = Field(default_factory=date.today)



class PhotoFoodItem(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    name: str = Field(min_length=1, max_length=160)
    estimated_grams: float = Field(gt=0, le=10000)
    calories_kcal: float = Field(ge=0, le=20000)
    protein_g: float = Field(ge=0, le=2000)
    carb_g: float = Field(ge=0, le=3000)
    fat_g: float = Field(ge=0, le=2000)
    confidence: float = Field(ge=0, le=1)


class PhotoAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[PhotoFoodItem] = Field(max_length=20)
    notes: str
    disclaimer: str


class PhotoConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[PhotoFoodItem] = Field(min_length=1, max_length=20)
    meal_type: MealType
    log_date: date = Field(default_factory=date.today)


class PhotoConfirmResponse(BaseModel):
    created_logs: list[FoodLogResponse]
