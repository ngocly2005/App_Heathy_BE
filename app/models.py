from datetime import UTC, date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'disabled')", name="ck_users_status"),
        UniqueConstraint("google_sub", name="uq_users_google_sub"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    google_sub: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    jti: Mapped[str] = mapped_column(String(36), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)



class HealthProfile(Base):
    __tablename__ = "health_profiles"
    __table_args__ = (
        CheckConstraint("sex IN ('male', 'female')", name="ck_health_profile_sex"),
        CheckConstraint("height_cm > 0", name="ck_health_profile_height"),
        CheckConstraint("weight_kg > 0", name="ck_health_profile_weight"),
        CheckConstraint(
            "activity_level IN ('sedentary', 'light', 'moderate', 'very_active')",
            name="ck_health_profile_activity",
        ),
        CheckConstraint(
            "goal IN ('lose', 'maintain', 'gain')",
            name="ck_health_profile_goal",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    birth_date: Mapped[date] = mapped_column(Date)
    sex: Mapped[str] = mapped_column(String(10))
    height_cm: Mapped[float] = mapped_column(Numeric(5, 2))
    weight_kg: Mapped[float] = mapped_column(Numeric(5, 2))
    activity_level: Mapped[str] = mapped_column(String(20))
    goal: Mapped[str] = mapped_column(String(20), default="maintain")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

class Food(Base):
    __tablename__ = "foods"
    __table_args__ = (
        CheckConstraint("calories_per_100g >= 0", name="ck_food_calories"),
        CheckConstraint("protein_per_100g >= 0", name="ck_food_protein"),
        CheckConstraint("carb_per_100g >= 0", name="ck_food_carbs"),
        CheckConstraint("fat_per_100g >= 0", name="ck_food_fat"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    calories_per_100g: Mapped[float] = mapped_column(Numeric(8, 2))
    protein_per_100g: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    carb_per_100g: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    fat_per_100g: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class FoodLog(Base):
    __tablename__ = "food_logs"
    __table_args__ = (
        CheckConstraint("grams > 0", name="ck_food_log_grams"),
        CheckConstraint("calories_kcal >= 0", name="ck_food_log_calories"),
        CheckConstraint("protein_g >= 0", name="ck_food_log_protein"),
        CheckConstraint("carb_g >= 0", name="ck_food_log_carbs"),
        CheckConstraint("fat_g >= 0", name="ck_food_log_fat"),
        CheckConstraint(
            "meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')",
            name="ck_food_log_meal_type",
        ),
        Index("ix_food_logs_user_date", "user_id", "log_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    food_id: Mapped[int | None] = mapped_column(
        ForeignKey("foods.id", ondelete="SET NULL")
    )
    log_date: Mapped[date] = mapped_column(Date)
    meal_type: Mapped[str] = mapped_column(String(20))
    grams: Mapped[float] = mapped_column(Numeric(8, 2))
    food_name: Mapped[str] = mapped_column(String(160))
    calories_kcal: Mapped[float] = mapped_column(Numeric(9, 2))
    protein_g: Mapped[float] = mapped_column(Numeric(9, 2), default=0)
    carb_g: Mapped[float] = mapped_column(Numeric(9, 2), default=0)
    fat_g: Mapped[float] = mapped_column(Numeric(9, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

class WaterLog(Base):
    __tablename__ = "water_logs"
    __table_args__ = (
        CheckConstraint("amount_ml > 0", name="ck_water_log_amount"),
        Index("ix_water_logs_user_date", "user_id", "log_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    log_date: Mapped[date] = mapped_column(Date)
    amount_ml: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )

class ActivityType(Base):
    __tablename__ = "activity_types"
    __table_args__ = (CheckConstraint("met > 0", name="ck_activity_type_met"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    met: Mapped[float] = mapped_column(Numeric(5, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)



class ActivityLog(Base):
    __tablename__ = "activity_logs"
    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="ck_activity_log_duration"),
        CheckConstraint("met_snapshot > 0", name="ck_activity_log_met"),
        CheckConstraint("calories_burned >= 0", name="ck_activity_log_calories"),
        Index("ix_activity_logs_user_date", "user_id", "log_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    activity_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("activity_types.id", ondelete="SET NULL")
    )
    log_date: Mapped[date] = mapped_column(Date)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    activity_name: Mapped[str] = mapped_column(String(120))
    met_snapshot: Mapped[float] = mapped_column(Numeric(5, 2))
    calories_burned: Mapped[float] = mapped_column(Numeric(9, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class WeightEntry(Base):
    __tablename__ = "weight_entries"
    __table_args__ = (
        UniqueConstraint("user_id", "measured_on", name="uq_weight_user_date"),
        CheckConstraint("weight_kg > 0", name="ck_weight_entry_weight"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    measured_on: Mapped[date] = mapped_column(Date)
    weight_kg: Mapped[float] = mapped_column(Numeric(5, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DiaryEntry(Base):
    __tablename__ = "diary_entries"
    __table_args__ = (
        UniqueConstraint("user_id", "entry_date", name="uq_diary_user_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    entry_date: Mapped[date] = mapped_column(Date)
    content: Mapped[str] = mapped_column(Text)
    mood: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )



class SavedMeal(Base):
    __tablename__ = "saved_meals"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_saved_meal_user_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class SavedMealItem(Base):
    __tablename__ = "saved_meal_items"
    __table_args__ = (
        CheckConstraint("grams > 0", name="ck_saved_meal_item_grams"),
        CheckConstraint("calories_per_100g >= 0", name="ck_saved_item_calories"),
        CheckConstraint("protein_per_100g >= 0", name="ck_saved_item_protein"),
        CheckConstraint("carb_per_100g >= 0", name="ck_saved_item_carbs"),
        CheckConstraint("fat_per_100g >= 0", name="ck_saved_item_fat"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    saved_meal_id: Mapped[int] = mapped_column(
        ForeignKey("saved_meals.id", ondelete="CASCADE"),
        index=True,
    )
    food_id: Mapped[int | None] = mapped_column(
        ForeignKey("foods.id", ondelete="SET NULL")
    )
    food_name: Mapped[str] = mapped_column(String(160))
    grams: Mapped[float] = mapped_column(Numeric(8, 2))
    calories_per_100g: Mapped[float] = mapped_column(Numeric(8, 2))
    protein_per_100g: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    carb_per_100g: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    fat_per_100g: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
