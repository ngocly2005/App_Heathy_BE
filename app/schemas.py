from app.core.dates import today as business_today
from datetime import date, datetime
from datetime import date as DateValue
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator, model_validator


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    status: str
    role: str = "user"
    google_sub: str | None
    has_password: bool = False
    created_at: datetime


class EmailLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class RegisterRequest(EmailLoginRequest):
    full_name: str = Field(min_length=1, max_length=120)
    password: SecretStr = Field(min_length=8, max_length=128)

    @field_validator("full_name", mode="before")
    @classmethod
    def trim_name(cls, value):
        if isinstance(value, str):
            if any(ord(ch) < 32 or 127 <= ord(ch) <= 159 for ch in value):
                raise ValueError("Name must not contain control characters")
            return value.strip()
        return value

    @field_validator("password")
    @classmethod
    def check_new_password(cls, value):
        return validate_new_password(value)


class PasswordUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: SecretStr | None = Field(default=None, min_length=1, max_length=128)
    new_password: SecretStr = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def check_new_password(cls, value):
        return validate_new_password(value)


def validate_new_password(value: SecretStr) -> SecretStr:
    password = value.get_secret_value()
    if not password.strip():
        raise ValueError("Password must not consist only of whitespace")
    if any(ord(ch) < 32 or 127 <= ord(ch) <= 159 for ch in password):
        raise ValueError("Password must not contain control characters")
    return value

class MealChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    question: str = Field(min_length=2, max_length=1000)
    date: DateValue = Field(default_factory=business_today)


class MealChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(description="The assistant's complete response or introduction to the detailed meals below.")
    suggestions: list[str] = Field(description="Full meal suggestions, including portions and estimated nutrition. These are part of the assistant message, not prompts to send.")
    disclaimer: str
    follow_up_questions: list[Annotated[str, Field(min_length=2, max_length=120)]] = Field(
        default_factory=list, max_length=4,
        description="Short follow-up questions the user may choose to ask next; never meal descriptions.")

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
ActivityLevel = Literal["sedentary", "light", "moderate", "very_active", "extra_active"]
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
        if birth_date >= business_today():
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
    grams: float = Field(ge=0.01, le=10000)
    meal_type: MealType
    log_date: date = Field(default_factory=business_today)
    meal_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class FoodLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    food_id: int | None
    log_date: date
    meal_type: str
    meal_time: str | None = None
    grams: float
    food_name: str
    calories_kcal: float
    protein_g: float
    carb_g: float
    fat_g: float
    created_at: datetime


class WaterLogCreate(BaseModel):
    amount_ml: int = Field(gt=0, le=5000)
    log_date: date = Field(default_factory=business_today)


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
    log_date: date = Field(default_factory=business_today)


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
    model_config = ConfigDict(allow_inf_nan=False, str_strip_whitespace=True)
    food_id: int | None = Field(default=None, gt=0)
    grams: float = Field(ge=0.01, le=10000)
    food_name: str | None = Field(default=None, min_length=1, max_length=160)
    calories_per_100g: float | None = Field(default=None, ge=0, le=20000)
    protein_per_100g: float = Field(default=0, ge=0, le=2000)
    carb_per_100g: float = Field(default=0, ge=0, le=3000)
    fat_per_100g: float = Field(default=0, ge=0, le=2000)

    @model_validator(mode="after")
    def snapshot_or_catalog(self):
        if self.food_id is None and (not self.food_name or self.calories_per_100g is None):
            raise ValueError("Provide food_id or food_name and nutrition snapshot")
        return self


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
    log_date: date = Field(default_factory=business_today)
    meal_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")



class PhotoFoodItem(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=160)
    estimated_grams: float = Field(ge=0.01, le=10000)
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
    log_date: date = Field(default_factory=business_today)
    meal_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class PhotoConfirmResponse(BaseModel):
    created_logs: list[FoodLogResponse]


class FoodLogUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)
    grams: float = Field(ge=0.01, le=10000)
    meal_type: MealType
    meal_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class WaterSettingsUpsert(BaseModel):
    target_ml: int | None = Field(default=None, ge=500, le=10000)
    serving_ml: Literal[200, 500] = 200


class WaterSettingsResponse(WaterSettingsUpsert):
    effective_target_ml: int


class WaterAdjustment(BaseModel):
    log_date: date
    amount_ml: Literal[-500, -200, 200, 500]


class WaterAdjustmentResponse(BaseModel):
    date: date
    total_ml: int


class NutritionSettingsUpsert(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    calorie_target: float | None = Field(default=None, ge=500, le=10000)
    protein_pct: int = Field(default=25, ge=0, le=100)
    carb_pct: int = Field(default=50, ge=0, le=100)
    fat_pct: int = Field(default=25, ge=0, le=100)
    target_weight_kg: float | None = Field(default=None, gt=20, le=400)

    @model_validator(mode="after")
    def percentages_sum_to_100(self):
        if self.protein_pct + self.carb_pct + self.fat_pct != 100:
            raise ValueError("Macro percentages must add to 100")
        return self


class AIInteractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    kind: str
    context_date: date
    question: str | None
    response: dict | None
    status: str
    error_code: int | None
    created_at: datetime
