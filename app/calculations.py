from datetime import date

ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "very_active": 1.725,
}


def calculate_age(birth_date: date, today: date | None = None) -> int:
    reference_date = today or date.today()
    birthday_passed = (reference_date.month, reference_date.day) >= (
        birth_date.month,
        birth_date.day,
    )
    return reference_date.year - birth_date.year - (not birthday_passed)


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    height_m = height_cm / 100
    return round(weight_kg / (height_m**2), 2)


def calculate_bmr(
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: str,
) -> float:
    sex_adjustment = 5 if sex == "male" else -161
    result = 10 * weight_kg + 6.25 * height_cm - 5 * age + sex_adjustment
    return round(result, 2)


def calculate_tdee(bmr_kcal: float, activity_level: str) -> float:
    return round(bmr_kcal * ACTIVITY_FACTORS[activity_level], 2)


def scale_nutrition(per_100g: float, grams: float) -> float:
    return round(per_100g * grams / 100, 2)


def calculate_activity_calories(
    met: float,
    weight_kg: float,
    duration_minutes: int,
) -> float:
    calories_per_minute = met * 3.5 * weight_kg / 200
    return round(calories_per_minute * duration_minutes, 2)


def calculate_macro_percentages(
    protein_g: float,
    carb_g: float,
    fat_g: float,
) -> tuple[float, float, float]:
    protein_kcal = protein_g * 4
    carb_kcal = carb_g * 4
    fat_kcal = fat_g * 9
    total_kcal = protein_kcal + carb_kcal + fat_kcal
    if total_kcal == 0:
        return 0.0, 0.0, 0.0
    return (
        round(protein_kcal / total_kcal * 100, 2),
        round(carb_kcal / total_kcal * 100, 2),
        round(fat_kcal / total_kcal * 100, 2),
    )