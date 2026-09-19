from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_from_directory,
    jsonify
)

import os
import threading
import time
from datetime import date, datetime, timedelta
from werkzeug.utils import secure_filename

from database import get_db, create_tables
from ocr import extract_text


# ============================================================
# APP SETUP
# ============================================================

app = Flask(__name__)

app.secret_key = "pet-care-secret-key"


# ============================================================
# FOLDERS
# ============================================================

PRESCRIPTION_FOLDER = "uploads/prescriptions"
MEAL_FOLDER = "uploads/meals"

app.config["PRESCRIPTION_FOLDER"] = PRESCRIPTION_FOLDER
app.config["MEAL_FOLDER"] = MEAL_FOLDER

os.makedirs(PRESCRIPTION_FOLDER, exist_ok=True)
os.makedirs(MEAL_FOLDER, exist_ok=True)


# ============================================================
# DATABASE
# ============================================================

create_tables()


# ============================================================
# DEFAULT MEAL NOTIFICATION TIMES
# ============================================================

DEFAULT_MEAL_NOTIFICATION_TIMES = {
    "breakfast": "08:00",
    "lunch": "13:00",
    "dinner": "20:00"
}


# ============================================================
# DATABASE COLUMN HELPER
# ============================================================

def ensure_column(table_name, column_name, column_definition):
    """
    Adds a column if an older database does not already contain it.
    This prevents errors when you update the project after creating
    the database.
    """

    try:
        conn = get_db()

        columns = conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()

        existing_columns = [
            row["name"] if hasattr(row, "keys") else row[1]
            for row in columns
        ]

        if column_name not in existing_columns:
            conn.execute(
                f"""
                ALTER TABLE {table_name}
                ADD COLUMN {column_name} {column_definition}
                """
            )
            conn.commit()

        conn.close()

    except Exception as e:
        print(
            f"DATABASE COLUMN ERROR "
            f"{table_name}.{column_name}:",
            e
        )


def ensure_database_columns():

    # Prescription columns
    ensure_column(
        "prescriptions",
        "status",
        "TEXT DEFAULT 'active'"
    )

    ensure_column(
        "prescriptions",
        "food_suggestions",
        "TEXT"
    )

    ensure_column(
        "prescriptions",
        "diagnosed_at",
        "TEXT"
    )

    ensure_column(
        "prescriptions",
        "treatment_start",
        "TEXT"
    )

    ensure_column(
        "prescriptions",
        "cured_at",
        "TEXT"
    )

    # User meal notification columns
    ensure_column(
        "users",
        "breakfast_time",
        "TEXT DEFAULT '08:00'"
    )

    ensure_column(
        "users",
        "lunch_time",
        "TEXT DEFAULT '13:00'"
    )

    ensure_column(
        "users",
        "dinner_time",
        "TEXT DEFAULT '20:00'"
    )


try:
    ensure_database_columns()
except Exception as e:
    print("DATABASE MIGRATION ERROR:", e)


# ============================================================
# CONTEXT PROCESSOR
# ============================================================
#
# IMPORTANT:
#
# This fixes:
#
# jinja2.exceptions.UndefinedError:
# 'meal_times' is undefined
#
# Now every template can use:
#
# {{ meal_times.breakfast }}
# {{ meal_times.lunch }}
# {{ meal_times.dinner }}
#
# ============================================================

@app.context_processor
def inject_global_data():

    meal_times = {
        "breakfast": DEFAULT_MEAL_NOTIFICATION_TIMES["breakfast"],
        "lunch": DEFAULT_MEAL_NOTIFICATION_TIMES["lunch"],
        "dinner": DEFAULT_MEAL_NOTIFICATION_TIMES["dinner"]
    }

    if "user_id" in session:

        try:

            conn = get_db()

            user = conn.execute(
                """
                SELECT
                    breakfast_time,
                    lunch_time,
                    dinner_time
                FROM users
                WHERE id = ?
                """,
                (session["user_id"],)
            ).fetchone()

            conn.close()

            if user:

                meal_times["breakfast"] = (
                    user["breakfast_time"]
                    or DEFAULT_MEAL_NOTIFICATION_TIMES["breakfast"]
                )

                meal_times["lunch"] = (
                    user["lunch_time"]
                    or DEFAULT_MEAL_NOTIFICATION_TIMES["lunch"]
                )

                meal_times["dinner"] = (
                    user["dinner_time"]
                    or DEFAULT_MEAL_NOTIFICATION_TIMES["dinner"]
                )

        except Exception as e:

            print(
                "GLOBAL MEAL TIME ERROR:",
                e
            )

    return {
        "meal_times": meal_times
    }


# ============================================================
# GET USER MEAL TIMES
# ============================================================

def get_user_meal_times(user_id):

    times = DEFAULT_MEAL_NOTIFICATION_TIMES.copy()

    try:

        conn = get_db()

        user = conn.execute(
            """
            SELECT
                breakfast_time,
                lunch_time,
                dinner_time
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        ).fetchone()

        conn.close()

        if user:

            times["breakfast"] = (
                user["breakfast_time"]
                or DEFAULT_MEAL_NOTIFICATION_TIMES["breakfast"]
            )

            times["lunch"] = (
                user["lunch_time"]
                or DEFAULT_MEAL_NOTIFICATION_TIMES["lunch"]
            )

            times["dinner"] = (
                user["dinner_time"]
                or DEFAULT_MEAL_NOTIFICATION_TIMES["dinner"]
            )

    except Exception as e:

        print(
            "GET MEAL TIMES ERROR:",
            e
        )

    return times


# ============================================================
# SEND DESKTOP NOTIFICATION
# ============================================================

def send_meal_notification(
    meal_type,
    pet_name,
    food
):

    try:

        from plyer import notification

        titles = {
            "breakfast": "🥣 Breakfast Time!",
            "lunch": "🍚 Lunch Time!",
            "dinner": "🍲 Dinner Time!"
        }

        title = titles.get(
            meal_type,
            "🐾 Pet Meal Reminder"
        )

        message = (
            f"{pet_name}'s {meal_type} is ready!\n\n"
            f"Suggested food:\n{food}"
        )

        notification.notify(
            title=title,
            message=message,
            app_name="Pet Care",
            timeout=10
        )

        print(
            f"NOTIFICATION SENT: "
            f"{meal_type} for {pet_name}"
        )

    except Exception as e:

        print(
            "NOTIFICATION ERROR:",
            e
        )


# ============================================================
# GET USERS FOR NOTIFICATION
# ============================================================

def get_notification_users():

    try:

        conn = get_db()

        users = conn.execute(
            """
            SELECT
                users.id AS user_id,
                pets.id AS pet_id,
                pets.name AS pet_name,
                pets.food_preference,
                pets.allergies
            FROM users
            INNER JOIN pets
                ON users.id = pets.user_id
            WHERE pets.id = (
                SELECT p2.id
                FROM pets p2
                WHERE p2.user_id = users.id
                ORDER BY p2.id DESC
                LIMIT 1
            )
            """
        ).fetchall()

        conn.close()

        return users

    except Exception as e:

        print(
            "NOTIFICATION USER ERROR:",
            e
        )

        return []


# ============================================================
# GET ACTIVE PRESCRIPTION FOR USER
# ============================================================

def get_active_prescription_for_user(user_id):

    try:

        conn = get_db()

        prescription = conn.execute(
            """
            SELECT *
            FROM prescriptions
            WHERE user_id = ?
            AND LOWER(
                TRIM(
                    COALESCE(status, 'active')
                )
            ) = 'active'
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,)
        ).fetchone()

        conn.close()

        return prescription

    except Exception as e:

        print(
            "NOTIFICATION PRESCRIPTION ERROR:",
            e
        )

        return None


# ============================================================
# NOTIFICATION WORKER
# ============================================================

def notification_worker():

    print("==========================================")
    print("MEAL NOTIFICATION SYSTEM STARTED")
    print("Default Breakfast : 08:00")
    print("Default Lunch     : 13:00")
    print("Default Dinner    : 20:00")
    print("==========================================")

    last_sent = {}

    while True:

        try:

            now = datetime.now()

            current_time = now.strftime("%H:%M")
            current_date = now.strftime("%Y-%m-%d")

            users = get_notification_users()

            for user in users:

                user_id = user["user_id"]

                meal_times = get_user_meal_times(
                    user_id
                )

                meal_type = None

                for meal, meal_time in meal_times.items():

                    if current_time == meal_time:

                        meal_type = meal
                        break

                if not meal_type:
                    continue

                notification_key = (
                    f"{current_date}_{meal_type}_{user_id}"
                )

                if last_sent.get(
                    notification_key
                ) == notification_key:

                    continue

                pet_name = (
                    user["pet_name"]
                    or "your pet"
                )

                prescription = (
                    get_active_prescription_for_user(
                        user_id
                    )
                )

                condition = "General"

                if prescription:

                    condition = (
                        prescription["condition"]
                        or detect_health_condition(
                            prescription["extracted_text"]
                        )
                    )

                food = (
                    get_meal_food_for_notification(
                        user,
                        condition,
                        meal_type
                    )
                )

                send_meal_notification(
                    meal_type,
                    pet_name,
                    food
                )

                last_sent[
                    notification_key
                ] = notification_key

            time.sleep(30)

        except Exception as e:

            print(
                "NOTIFICATION WORKER ERROR:",
                e
            )

            time.sleep(30)


# ============================================================
# START NOTIFICATION THREAD
# ============================================================

def start_notification_worker():

    thread = threading.Thread(
        target=notification_worker,
        daemon=True
    )

    thread.start()


# ============================================================
# SERVE PRESCRIPTION IMAGES
# ============================================================

@app.route(
    "/uploads/prescriptions/<filename>"
)
def uploaded_prescription(filename):

    return send_from_directory(
        app.config["PRESCRIPTION_FOLDER"],
        filename
    )


# ============================================================
# SERVE MEAL IMAGES
# ============================================================

@app.route(
    "/uploads/meals/<filename>"
)
def uploaded_meal(filename):

    return send_from_directory(
        app.config["MEAL_FOLDER"],
        filename
    )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# INDEX
# ============================================================

@app.route("/index")
def index():

    return redirect(
        url_for("home")
    )


# ============================================================
# SIGNUP
# ============================================================

@app.route(
    "/signup",
    methods=["GET", "POST"]
)
def signup():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not name or not email or not password:

            return render_template(
                "signup.html",
                error="Please fill all fields."
            )

        conn = get_db()

        existing_user = conn.execute(
            """
            SELECT id
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        if existing_user:

            conn.close()

            return render_template(
                "signup.html",
                error=(
                    "Email already registered. "
                    "Please login."
                )
            )

        conn.execute(
            """
            INSERT INTO users
            (
                name,
                email,
                password
            )
            VALUES (?, ?, ?)
            """,
            (
                name,
                email,
                password
            )
        )

        conn.commit()
        conn.close()

        flash(
            "Account created successfully. Please login."
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "signup.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not email or not password:

            return render_template(
                "login.html",
                error=(
                    "Please enter email "
                    "and password."
                )
            )

        conn = get_db()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE LOWER(email) = ?
            AND password = ?
            """,
            (
                email,
                password
            )
        ).fetchone()

        conn.close()

        if user:

            session.clear()

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            return redirect(
                url_for("dashboard")
            )

        return render_template(
            "login.html",
            error="Invalid email or password."
        )

    return render_template(
        "login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out."
    )

    return redirect(
        url_for("home")
    )


# ============================================================
# GET CURRENT PET
# ============================================================

def get_pet():

    if "user_id" not in session:

        return None

    conn = get_db()

    pet = conn.execute(
        """
        SELECT *
        FROM pets
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            session["user_id"],
        )
    ).fetchone()

    conn.close()

    return pet


# ============================================================
# NORMALIZE STATUS
# ============================================================

def normalize_status(status):

    status = str(
        status or ""
    ).strip().lower()

    if status == "cured":

        return "cured"

    return "active"


# ============================================================
# NORMALIZE DATABASE STATUSES
# ============================================================

def normalize_database_statuses():

    try:

        conn = get_db()

        conn.execute(
            """
            UPDATE prescriptions
            SET status = 'active'
            WHERE status IS NULL
            OR TRIM(status) = ''
            """
        )

        conn.execute(
            """
            UPDATE prescriptions
            SET status = 'active'
            WHERE LOWER(TRIM(status)) = 'active'
            """
        )

        conn.execute(
            """
            UPDATE prescriptions
            SET status = 'cured'
            WHERE LOWER(TRIM(status)) = 'cured'
            """
        )

        conn.commit()
        conn.close()

    except Exception as e:

        print(
            "STATUS NORMALIZATION ERROR:",
            e
        )


# ============================================================
# DETECT HEALTH CONDITION
# ============================================================

def detect_health_condition(
    prescription_text
):

    text = (
        prescription_text or ""
    ).lower()

    text = " ".join(
        text.split()
    )

    if any(
        word in text
        for word in [
            "diabetes mellitus",
            "diabetes",
            "diabetic",
            "diabetis",
            "diabetic mellitus"
        ]
    ):

        return "Diabetes"

    if any(
        word in text
        for word in [
            "kidney disease",
            "kidney problem",
            "kidney",
            "renal disease",
            "renal problem",
            "renal",
            "nephritis",
            "nephropathy",
            "chronic kidney"
        ]
    ):

        return "Kidney Disease"

    if any(
        word in text
        for word in [
            "liver disease",
            "liver problem",
            "liver",
            "hepatic",
            "hepatitis"
        ]
    ):

        return "Liver Disease"

    if any(
        word in text
        for word in [
            "obesity",
            "obese",
            "overweight",
            "weight management",
            "weight loss"
        ]
    ):

        return "Obesity"

    if any(
        word in text
        for word in [
            "gastritis",
            "gastric",
            "stomach inflammation"
        ]
    ):

        return "Gastritis"

    if any(
        word in text
        for word in [
            "arthritis",
            "joint disease",
            "joint problem",
            "osteoarthritis"
        ]
    ):

        return "Arthritis"

    if any(
        word in text
        for word in [
            "anemia",
            "anaemia",
            "anemic",
            "anaemic"
        ]
    ):

        return "Anemia"

    return "General"


# ============================================================
# FOOD DATABASE
# ============================================================

FOOD_DATABASE = {

    "Diabetes": {

        "veg": [
            "Boiled green beans",
            "Steamed broccoli",
            "Cooked zucchini",
            "Small portion of cooked pumpkin",
            "Veterinarian-approved high-fiber pet food"
        ],

        "nonveg": [
            "Boiled skinless chicken breast",
            "Boiled turkey",
            "Cooked egg whites",
            "Boiled lean fish",
            "Veterinarian-approved high-fiber pet food"
        ]
    },

    "Kidney Disease": {

        "veg": [
            "Cooked white rice",
            "Cooked green beans",
            "Cooked zucchini",
            "Small amount of cooked pumpkin",
            "Veterinarian-approved renal food"
        ],

        "nonveg": [
            "Boiled egg whites",
            "Veterinarian-approved portion of boiled chicken",
            "Veterinarian-approved portion of cooked fish",
            "Cooked white rice",
            "Veterinarian-approved renal food"
        ]
    },

    "Liver Disease": {

        "veg": [
            "Cooked white rice",
            "Cooked pumpkin",
            "Cooked carrots",
            "Cooked green beans",
            "Veterinarian-approved liver-support food"
        ],

        "nonveg": [
            "Boiled skinless chicken breast",
            "Cooked egg whites",
            "Boiled white fish",
            "Cooked white rice",
            "Veterinarian-approved liver-support food"
        ]
    },

    "Obesity": {

        "veg": [
            "Steamed green beans",
            "Cooked zucchini",
            "Cooked carrots in a controlled portion",
            "Small amount of cooked pumpkin",
            "Complete weight-management pet food"
        ],

        "nonveg": [
            "Boiled skinless chicken breast",
            "Boiled turkey breast",
            "Cooked white fish",
            "Steamed green beans",
            "Complete weight-management pet food"
        ]
    },

    "Gastritis": {

        "veg": [
            "Plain cooked white rice",
            "Plain cooked pumpkin",
            "Boiled potato without seasoning",
            "Cooked carrots",
            "Veterinarian-approved easily digestible pet food"
        ],

        "nonveg": [
            "Boiled skinless chicken breast",
            "Plain cooked white rice",
            "Boiled turkey",
            "Plain cooked pumpkin",
            "Veterinarian-approved easily digestible pet food"
        ]
    },

    "Arthritis": {

        "veg": [
            "Cooked green beans",
            "Cooked pumpkin",
            "Cooked carrots",
            "Cooked zucchini",
            "Complete pet food appropriate for healthy weight"
        ],

        "nonveg": [
            "Cooked salmon in a veterinarian-approved portion",
            "Boiled skinless chicken breast",
            "Cooked sardines only if veterinarian-approved",
            "Cooked turkey",
            "Complete pet food appropriate for healthy weight"
        ]
    },

    "Anemia": {

        "veg": [
            "Cooked lentils if veterinarian-approved",
            "Cooked spinach in a small amount",
            "Cooked pumpkin",
            "Cooked green beans",
            "Complete balanced pet food"
        ],

        "nonveg": [
            "Boiled lean beef in a veterinarian-approved portion",
            "Boiled chicken",
            "Cooked egg",
            "Cooked turkey",
            "Complete balanced pet food"
        ]
    },

    "General": {

        "veg": [
            "Cooked pumpkin",
            "Cooked green beans",
            "Cooked carrots",
            "Cooked zucchini",
            "Complete and balanced pet food"
        ],

        "nonveg": [
            "Boiled skinless chicken",
            "Cooked turkey",
            "Cooked egg",
            "Cooked fish",
            "Complete and balanced pet food"
        ]
    }
}


# ============================================================
# CHECK NON-VEGETARIAN
# ============================================================

def is_non_vegetarian(pet):

    if not pet:

        return False

    preference = (
        pet["food_preference"]
        or ""
    ).lower().strip()

    return (
        "non vegetarian" in preference
        or "non-vegetarian" in preference
        or "non veg" in preference
        or "nonveg" in preference
        or "non-veg" in preference
    )


# ============================================================
# REMOVE ALLERGIC FOODS
# ============================================================

def remove_allergic_foods(
    suggestions,
    pet
):

    if not pet:

        return suggestions

    allergies = (
        pet["allergies"]
        or ""
    ).lower()

    allergy_list = [
        item.strip()
        for item in allergies.split(",")
        if item.strip()
    ]

    if not allergy_list:

        return suggestions

    safe_suggestions = []

    for suggestion in suggestions:

        suggestion_lower = (
            suggestion.lower()
        )

        has_allergy = any(
            allergy in suggestion_lower
            for allergy in allergy_list
        )

        if not has_allergy:

            safe_suggestions.append(
                suggestion
            )

    return safe_suggestions


# ============================================================
# GET FOOD SUGGESTIONS
# ============================================================

def get_food_suggestions(
    pet,
    condition
):

    if condition not in FOOD_DATABASE:

        condition = "General"

    if is_non_vegetarian(pet):

        suggestions = FOOD_DATABASE[
            condition
        ]["nonveg"].copy()

    else:

        suggestions = FOOD_DATABASE[
            condition
        ]["veg"].copy()

    suggestions = remove_allergic_foods(
        suggestions,
        pet
    )

    if not suggestions:

        return [
            "⚠️ No safe food was found after applying the listed allergies.",
            "Please follow your veterinarian's dietary instructions."
        ]

    return suggestions


# ============================================================
# PORTION PLAN
# ============================================================

def get_portion_plan():

    return {

        "breakfast": {
            "percentage": 30,
            "label": (
                "30% of the recommended daily amount"
            )
        },

        "lunch": {
            "percentage": 35,
            "label": (
                "35% of the recommended daily amount"
            )
        },

        "dinner": {
            "percentage": 35,
            "label": (
                "35% of the recommended daily amount"
            )
        }
    }


# ============================================================
# CREATE FOOD PLAN
# ============================================================

def create_food_plan(
    pet,
    condition
):

    foods = get_food_suggestions(
        pet,
        condition
    )

    portions = get_portion_plan()

    breakfast = (
        foods[0]
        if len(foods) > 0
        else "No recommendation"
    )

    lunch = (
        foods[1]
        if len(foods) > 1
        else breakfast
    )

    dinner = (
        foods[2]
        if len(foods) > 2
        else lunch
    )

    return {

        "breakfast": {
            "food": breakfast,
            "portion": portions[
                "breakfast"
            ]["label"],
            "percentage": portions[
                "breakfast"
            ]["percentage"]
        },

        "lunch": {
            "food": lunch,
            "portion": portions[
                "lunch"
            ]["label"],
            "percentage": portions[
                "lunch"
            ]["percentage"]
        },

        "dinner": {
            "food": dinner,
            "portion": portions[
                "dinner"
            ]["label"],
            "percentage": portions[
                "dinner"
            ]["percentage"]
        }
    }


# ============================================================
# FORMAT FOOD SUGGESTIONS
# ============================================================

def format_food_suggestions(
    pet,
    condition
):

    plan = create_food_plan(
        pet,
        condition
    )

    result = [

        f"🥣 Breakfast: "
        f"{plan['breakfast']['food']}",

        f"Portion: "
        f"{plan['breakfast']['portion']}",

        "",

        f"🍚 Lunch: "
        f"{plan['lunch']['food']}",

        f"Portion: "
        f"{plan['lunch']['portion']}",

        "",

        f"🍲 Dinner: "
        f"{plan['dinner']['food']}",

        f"Portion: "
        f"{plan['dinner']['portion']}",

        "",

        "💧 Fresh drinking water should always be available.",

        "⚠️ Portion percentages apply to the veterinarian/food-label recommended DAILY amount.",

        "⚠️ Do not use these suggestions to replace a prescribed therapeutic diet."
    ]

    return "\n".join(result)


# ============================================================
# MEAL FOOD FOR NOTIFICATION
# ============================================================

def get_meal_food_for_notification(
    user,
    condition,
    meal_type
):

    try:

        pet = {
            "food_preference": user["food_preference"],
            "allergies": user["allergies"]
        }

        plan = create_food_plan(
            pet,
            condition
        )

        return plan[
            meal_type
        ]["food"]

    except Exception as e:

        print(
            "MEAL FOOD ERROR:",
            e
        )

        return (
            "Follow the veterinarian-approved meal plan."
        )


# ============================================================
# GET ACTIVE PRESCRIPTION
# ============================================================

def get_active_prescription(
    user_id
):

    normalize_database_statuses()

    conn = get_db()

    prescription = conn.execute(
        """
        SELECT *
        FROM prescriptions
        WHERE user_id = ?
        AND LOWER(
            TRIM(
                COALESCE(status, 'active')
            )
        ) = 'active'
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            user_id,
        )
    ).fetchone()

    conn.close()

    return prescription


# ============================================================
# GET TREATMENT DAY
# ============================================================

def get_treatment_day(
    prescription
):

    if not prescription:

        return 0

    start_value = None

    try:
        start_value = prescription[
            "treatment_start"
        ]
    except Exception:
        pass

    if not start_value:

        try:
            start_value = prescription[
                "uploaded_at"
            ]
        except Exception:
            pass

    if not start_value:

        return 1

    try:

        start_date = datetime.strptime(
            str(start_value)[:10],
            "%Y-%m-%d"
        ).date()

        days = (
            date.today() - start_date
        ).days + 1

        return max(
            1,
            days
        )

    except Exception:

        return 1


# ============================================================
# PET PROFILE
# ============================================================

@app.route(
    "/pet-profile",
    methods=["GET", "POST"]
)
def pet_profile():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    pet = get_pet()

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        pet_type = request.form.get(
            "pet_type",
            ""
        ).strip()

        breed = request.form.get(
            "breed",
            ""
        ).strip()

        age = request.form.get(
            "age",
            ""
        ).strip()

        weight = request.form.get(
            "weight",
            ""
        ).strip()

        activity = request.form.get(
            "activity",
            ""
        ).strip()

        food_preference = request.form.get(
            "food_preference",
            ""
        ).strip()

        allergies = request.form.get(
            "allergies",
            ""
        ).strip()

        veterinarian = request.form.get(
            "veterinarian",
            ""
        ).strip()

        if not name:

            return render_template(
                "pet_profile.html",
                pet=pet,
                error=(
                    "Please enter your pet's name."
                )
            )

        conn = get_db()

        if pet:

            conn.execute(
                """
                UPDATE pets
                SET
                    name = ?,
                    pet_type = ?,
                    breed = ?,
                    age = ?,
                    weight = ?,
                    activity = ?,
                    food_preference = ?,
                    allergies = ?,
                    veterinarian = ?
                WHERE id = ?
                """,
                (
                    name,
                    pet_type,
                    breed,
                    age,
                    weight,
                    activity,
                    food_preference,
                    allergies,
                    veterinarian,
                    pet["id"]
                )
            )

        else:

            conn.execute(
                """
                INSERT INTO pets
                (
                    user_id,
                    name,
                    pet_type,
                    breed,
                    age,
                    weight,
                    activity,
                    food_preference,
                    allergies,
                    veterinarian
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session["user_id"],
                    name,
                    pet_type,
                    breed,
                    age,
                    weight,
                    activity,
                    food_preference,
                    allergies,
                    veterinarian
                )
            )

        conn.commit()
        conn.close()

        flash(
            "Pet profile saved successfully!"
        )

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "pet_profile.html",
        pet=pet
    )


# ============================================================
# PRESCRIPTION
# ============================================================

@app.route(
    "/prescription",
    methods=["GET", "POST"]
)
def prescription():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    normalize_database_statuses()

    pet = get_pet()

    if not pet:

        return redirect(
            url_for("pet_profile")
        )

    # --------------------------------------------------------
    # UPLOAD
    # --------------------------------------------------------

    if request.method == "POST":

        file = request.files.get(
            "prescription"
        )

        if not file or file.filename == "":

            flash(
                "Please select a prescription image."
            )

            return redirect(
                url_for("prescription")
            )

        filename = secure_filename(
            file.filename
        )

        if "." not in filename:

            flash(
                "Invalid image file."
            )

            return redirect(
                url_for("prescription")
            )

        extension = filename.rsplit(
            ".",
            1
        )[1].lower()

        if extension not in [
            "jpg",
            "jpeg",
            "png",
            "webp"
        ]:

            flash(
                "Please upload JPG, JPEG, PNG or WEBP."
            )

            return redirect(
                url_for("prescription")
            )

        timestamp = datetime.now().strftime(
            "%Y%m%d%H%M%S%f"
        )

        filename = (
            timestamp
            + "_"
            + filename
        )

        filepath = os.path.join(
            app.config["PRESCRIPTION_FOLDER"],
            filename
        )

        file.save(
            filepath
        )

        # ----------------------------------------------------
        # OCR
        # ----------------------------------------------------

        try:

            extracted_text = extract_text(
                filepath
            )

        except Exception as e:

            print(
                "OCR ERROR:",
                e
            )

            extracted_text = ""

        print(
            "\n=============================="
        )

        print(
            "EXTRACTED PRESCRIPTION TEXT"
        )

        print(
            "=============================="
        )

        print(
            extracted_text
        )

        print(
            "==============================\n"
        )

        # ----------------------------------------------------
        # CONDITION
        # ----------------------------------------------------

        condition = detect_health_condition(
            extracted_text
        )

        print(
            "DETECTED CONDITION:",
            condition
        )

        food_suggestions = (
            format_food_suggestions(
                pet,
                condition
            )
        )

        today = date.today().strftime(
            "%Y-%m-%d"
        )

        uploaded_at = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        conn = get_db()

        cursor = conn.execute(
            """
            INSERT INTO prescriptions
            (
                user_id,
                pet_id,
                filename,
                extracted_text,
                condition,
                uploaded_at,
                food_suggestions,
                status,
                diagnosed_at,
                treatment_start
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                pet["id"],
                filename,
                extracted_text,
                condition,
                uploaded_at,
                food_suggestions,
                "active",
                today,
                today
            )
        )

        prescription_id = cursor.lastrowid

        conn.commit()
        conn.close()

        flash(
            "Prescription uploaded and analyzed successfully."
        )

        return redirect(
            url_for(
                "review",
                prescription_id=prescription_id
            )
        )

    # --------------------------------------------------------
    # PREVIOUS PRESCRIPTIONS
    # --------------------------------------------------------

    conn = get_db()

    rows = conn.execute(
        """
        SELECT *
        FROM prescriptions
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (
            session["user_id"],
        )
    ).fetchall()

    conn.close()

    prescriptions = []

    for row in rows:

        data = dict(row)

        condition = (
            data.get("condition")
            or detect_health_condition(
                data.get(
                    "extracted_text",
                    ""
                )
            )
        )

        data["condition"] = condition

        status = normalize_status(
            data.get("status")
        )

        data["status"] = status

        if status == "active":

            data["food_suggestions"] = (
                format_food_suggestions(
                    pet,
                    condition
                )
            )

        else:

            data["food_suggestions"] = (
                "🎉 This condition has been marked as cured."
            )

        data["treatment_day"] = (
            get_treatment_day(
                data
            )
        )

        prescriptions.append(
            data
        )

    return render_template(
        "prescription.html",
        pet=pet,
        prescriptions=prescriptions
    )


# ============================================================
# UPLOAD PRESCRIPTION COMPATIBILITY ROUTE
# ============================================================

@app.route(
    "/upload-prescription",
    methods=["POST"]
)
def upload_prescription():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    return prescription()


# ============================================================
# REVIEW
# ============================================================

@app.route(
    "/review/<int:prescription_id>"
)
def review(
    prescription_id
):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    conn = get_db()

    prescription = conn.execute(
        """
        SELECT *
        FROM prescriptions
        WHERE id = ?
        AND user_id = ?
        """,
        (
            prescription_id,
            session["user_id"]
        )
    ).fetchone()

    pet = conn.execute(
        """
        SELECT *
        FROM pets
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            session["user_id"],
        )
    ).fetchone()

    conn.close()

    if not prescription:

        flash(
            "Prescription not found."
        )

        return redirect(
            url_for("prescription")
        )

    prescription = dict(
        prescription
    )

    condition = (
        prescription.get("condition")
        or detect_health_condition(
            prescription.get(
                "extracted_text",
                ""
            )
        )
    )

    prescription["condition"] = condition

    status = normalize_status(
        prescription.get("status")
    )

    prescription["status"] = status

    prescription["treatment_day"] = (
        get_treatment_day(
            prescription
        )
    )

    if status == "active":

        prescription["food_suggestions"] = (
            format_food_suggestions(
                pet,
                condition
            )
        )

    else:

        prescription["food_suggestions"] = (
            "🎉 This condition has been marked as cured."
        )

    return render_template(
        "review.html",
        prescription=prescription,
        pet=pet
    )


# ============================================================
# START TREATMENT
# ============================================================

@app.route(
    "/start-treatment/<int:prescription_id>",
    methods=["POST"]
)
def start_treatment(
    prescription_id
):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    today = date.today().strftime(
        "%Y-%m-%d"
    )

    conn = get_db()

    updated = conn.execute(
        """
        UPDATE prescriptions
        SET
            status = 'active',
            treatment_start = ?,
            cured_at = NULL
        WHERE id = ?
        AND user_id = ?
        """,
        (
            today,
            prescription_id,
            session["user_id"]
        )
    )

    conn.commit()

    success = (
        updated.rowcount > 0
    )

    conn.close()

    if success:

        flash(
            "Treatment started successfully."
        )

    else:

        flash(
            "Prescription not found."
        )

    return redirect(
        url_for(
            "review",
            prescription_id=prescription_id
        )
    )


# ============================================================
# MARK CURED
# ============================================================

@app.route(
    "/mark-cured/<int:prescription_id>",
    methods=["POST"]
)
def mark_cured(
    prescription_id
):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    today = date.today().strftime(
        "%Y-%m-%d"
    )

    conn = get_db()

    updated = conn.execute(
        """
        UPDATE prescriptions
        SET
            status = 'cured',
            cured_at = ?
        WHERE id = ?
        AND user_id = ?
        """,
        (
            today,
            prescription_id,
            session["user_id"]
        )
    )

    conn.commit()

    success = (
        updated.rowcount > 0
    )

    conn.close()

    if success:

        flash(
            "🎉 Condition marked as cured."
        )

    else:

        flash(
            "Prescription not found."
        )

    return redirect(
        url_for("prescription")
    )


# ============================================================
# RESTART TREATMENT
# ============================================================

@app.route(
    "/restart-treatment/<int:prescription_id>",
    methods=["POST"]
)
def restart_treatment(
    prescription_id
):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    today = date.today().strftime(
        "%Y-%m-%d"
    )

    conn = get_db()

    updated = conn.execute(
        """
        UPDATE prescriptions
        SET
            status = 'active',
            treatment_start = ?,
            cured_at = NULL
        WHERE id = ?
        AND user_id = ?
        """,
        (
            today,
            prescription_id,
            session["user_id"]
        )
    )

    conn.commit()

    success = (
        updated.rowcount > 0
    )

    conn.close()

    if success:

        flash(
            "Treatment restarted successfully."
        )

    else:

        flash(
            "Prescription not found."
        )

    return redirect(
        url_for(
            "review",
            prescription_id=prescription_id
        )
    )


# ============================================================
# DELETE PRESCRIPTION
# ============================================================

@app.route(
    "/delete-prescription/<int:prescription_id>",
    methods=["POST"]
)
def delete_prescription(
    prescription_id
):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    conn = get_db()

    prescription = conn.execute(
        """
        SELECT *
        FROM prescriptions
        WHERE id = ?
        AND user_id = ?
        """,
        (
            prescription_id,
            session["user_id"]
        )
    ).fetchone()

    if not prescription:

        conn.close()

        flash(
            "Prescription not found."
        )

        return redirect(
            url_for("prescription")
        )

    filename = prescription[
        "filename"
    ]

    if filename:

        filepath = os.path.join(
            app.config[
                "PRESCRIPTION_FOLDER"
            ],
            filename
        )

        if os.path.exists(filepath):

            try:

                os.remove(filepath)

            except OSError as e:

                print(
                    "IMAGE DELETE ERROR:",
                    e
                )

    conn.execute(
        """
        DELETE FROM prescriptions
        WHERE id = ?
        AND user_id = ?
        """,
        (
            prescription_id,
            session["user_id"]
        )
    )

    conn.commit()
    conn.close()

    flash(
        "🗑 Prescription deleted successfully."
    )

    return redirect(
        url_for("prescription")
    )


# ============================================================
# DIET PLAN
# ============================================================

@app.route("/diet-plan")
def diet_plan():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    pet = get_pet()

    if not pet:

        return redirect(
            url_for("pet_profile")
        )

    prescription = get_active_prescription(
        session["user_id"]
    )

    suggestions = []
    food_plan = {}
    condition = "General"
    treatment_day = 0

    if prescription:

        condition = (
            prescription["condition"]
            or detect_health_condition(
                prescription["extracted_text"]
            )
        )

        suggestions = get_food_suggestions(
            pet,
            condition
        )

        food_plan = create_food_plan(
            pet,
            condition
        )

        treatment_day = get_treatment_day(
            prescription
        )

    return render_template(
        "diet_plan.html",
        pet=pet,
        prescription=prescription,
        suggestions=suggestions,
        food_plan=food_plan,
        condition=condition,
        treatment_day=treatment_day
    )


# ============================================================
# VERIFY MEAL PHOTO
# ============================================================

def verify_meal_photo(
    image_path
):

    try:

        from PIL import Image
        import numpy as np

        image = Image.open(
            image_path
        ).convert("RGB")

        width, height = image.size

        if width < 150 or height < 150:

            return False

        image.thumbnail(
            (500, 500)
        )

        array = np.array(
            image
        )

        brightness = array.mean()

        if brightness < 8:
            return False

        if brightness > 248:
            return False

        if array.std() < 5:
            return False

        return True

    except Exception as e:

        print(
            "MEAL PHOTO ERROR:",
            e
        )

        return False


# ============================================================
# GET COMPLETED MEAL DAYS
# ============================================================
#
# A day is considered COMPLETE only if:
#
# breakfast + lunch + dinner
#
# are all uploaded.
#
# ============================================================

def get_completed_meal_dates(
    user_id
):

    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            date,
            COUNT(DISTINCT meal_type) AS meal_count
        FROM meals
        WHERE user_id = ?
        AND meal_type IN (
            'breakfast',
            'lunch',
            'dinner'
        )
        GROUP BY date
        ORDER BY date DESC
        """,
        (
            user_id,
        )
    ).fetchall()

    conn.close()

    completed_dates = []

    for row in rows:

        if row["meal_count"] == 3:

            try:

                meal_date = datetime.strptime(
                    row["date"],
                    "%Y-%m-%d"
                ).date()

                completed_dates.append(
                    meal_date
                )

            except (
                ValueError,
                TypeError
            ):

                pass

    return completed_dates


# ============================================================
# CURRENT STREAK
# ============================================================
#
# IMPORTANT:
#
# If today is not complete -> 0
#
# If yesterday was missed -> streak breaks.
#
# Example:
#
# Sept 1  = complete
# Sept 2  = complete
# Sept 3  = MISSED
# Sept 4  = complete
#
# Current streak = 1
#
# ============================================================

def calculate_streak(
    user_id
):

    dates = get_completed_meal_dates(
        user_id
    )

    if not dates:

        return 0

    today = date.today()

    # Today must be complete.
    if dates[0] != today:

        return 0

    streak = 0

    expected_date = today

    for meal_date in dates:

        if meal_date == expected_date:

            streak += 1

            expected_date = (
                expected_date
                - timedelta(days=1)
            )

        elif meal_date < expected_date:

            # A day was missed.
            break

    return streak


# ============================================================
# LONGEST STREAK
# ============================================================

def calculate_longest_streak(
    user_id
):

    dates = get_completed_meal_dates(
        user_id
    )

    if not dates:

        return 0

    dates = sorted(
        set(dates)
    )

    longest = 1
    current = 1

    for i in range(
        1,
        len(dates)
    ):

        difference = (
            dates[i] - dates[i - 1]
        ).days

        if difference == 1:

            current += 1

        else:

            current = 1

        longest = max(
            longest,
            current
        )

    return longest


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    pet = get_pet()

    conn = get_db()

    meals = conn.execute(
        """
        SELECT *
        FROM meals
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 5
        """,
        (
            user_id,
        )
    ).fetchall()

    prescription = conn.execute(
        """
        SELECT *
        FROM prescriptions
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            user_id,
        )
    ).fetchone()

    conn.close()

    streak = calculate_streak(
        user_id
    )

    treatment_day = get_treatment_day(
        prescription
    )

    meal_times = get_user_meal_times(
        user_id
    )

    return render_template(
        "dashboard.html",
        pet=pet,
        meals=meals,
        prescription=prescription,
        streak=streak,
        treatment_day=treatment_day,
        meal_times=meal_times
    )


# ============================================================
# MEAL NOTIFICATIONS API
# ============================================================

@app.route("/meal-notifications")
def meal_notifications():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "logged_in": False,
            "notifications": []
        })

    pet = get_pet()

    if not pet:

        return jsonify({
            "success": False,
            "logged_in": True,
            "has_pet": False,
            "notifications": []
        })

    prescription = get_active_prescription(
        session["user_id"]
    )

    condition = "General"

    if prescription:

        condition = (
            prescription["condition"]
            or detect_health_condition(
                prescription["extracted_text"]
            )
        )

    food_plan = create_food_plan(
        pet,
        condition
    )

    meal_times = get_user_meal_times(
        session["user_id"]
    )

    notifications = [

        {
            "meal_type": "breakfast",
            "time": meal_times["breakfast"],
            "food": food_plan[
                "breakfast"
            ]["food"],
            "portion": food_plan[
                "breakfast"
            ]["portion"],
            "message": (
                f"Good morning! "
                f"{pet['name']}'s breakfast is ready. "
                f"Suggested food: "
                f"{food_plan['breakfast']['food']}. "
                f"{food_plan['breakfast']['portion']}."
            )
        },

        {
            "meal_type": "lunch",
            "time": meal_times["lunch"],
            "food": food_plan[
                "lunch"
            ]["food"],
            "portion": food_plan[
                "lunch"
            ]["portion"],
            "message": (
                f"It's lunch time for "
                f"{pet['name']}! "
                f"Suggested food: "
                f"{food_plan['lunch']['food']}. "
                f"{food_plan['lunch']['portion']}."
            )
        },

        {
            "meal_type": "dinner",
            "time": meal_times["dinner"],
            "food": food_plan[
                "dinner"
            ]["food"],
            "portion": food_plan[
                "dinner"
            ]["portion"],
            "message": (
                f"Dinner time for "
                f"{pet['name']}! "
                f"Suggested food: "
                f"{food_plan['dinner']['food']}. "
                f"{food_plan['dinner']['portion']}."
            )
        }
    ]

    return jsonify({

        "success": True,

        "logged_in": True,

        "has_pet": True,

        "pet_name": pet["name"],

        "condition": condition,

        "meal_times": meal_times,

        "notifications": notifications
    })


# ============================================================
# MEAL NOTIFICATION SETTINGS
# ============================================================

@app.route(
    "/meal-notification-settings",
    methods=["GET", "POST"]
)
def meal_notification_settings():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    if request.method == "POST":

        breakfast_time = request.form.get(
            "breakfast_time",
            DEFAULT_MEAL_NOTIFICATION_TIMES[
                "breakfast"
            ]
        ).strip()

        lunch_time = request.form.get(
            "lunch_time",
            DEFAULT_MEAL_NOTIFICATION_TIMES[
                "lunch"
            ]
        ).strip()

        dinner_time = request.form.get(
            "dinner_time",
            DEFAULT_MEAL_NOTIFICATION_TIMES[
                "dinner"
            ]
        ).strip()

        def valid_time(value):

            try:

                datetime.strptime(
                    value,
                    "%H:%M"
                )

                return True

            except ValueError:

                return False

        if not valid_time(
            breakfast_time
        ):

            breakfast_time = (
                DEFAULT_MEAL_NOTIFICATION_TIMES[
                    "breakfast"
                ]
            )

        if not valid_time(
            lunch_time
        ):

            lunch_time = (
                DEFAULT_MEAL_NOTIFICATION_TIMES[
                    "lunch"
                ]
            )

        if not valid_time(
            dinner_time
        ):

            dinner_time = (
                DEFAULT_MEAL_NOTIFICATION_TIMES[
                    "dinner"
                ]
            )

        conn = get_db()

        conn.execute(
            """
            UPDATE users
            SET
                breakfast_time = ?,
                lunch_time = ?,
                dinner_time = ?
            WHERE id = ?
            """,
            (
                breakfast_time,
                lunch_time,
                dinner_time,
                session["user_id"]
            )
        )

        conn.commit()
        conn.close()

        # Also keep session values for compatibility.
        session["breakfast_time"] = (
            breakfast_time
        )

        session["lunch_time"] = (
            lunch_time
        )

        session["dinner_time"] = (
            dinner_time
        )

        session.modified = True

        flash(
            "🔔 Meal notification times saved successfully!"
        )

        return redirect(
            url_for(
                "meal_notification_settings"
            )
        )

    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    meal_times = get_user_meal_times(
        session["user_id"]
    )

    return render_template(
        "meal_notification_settings.html",

        breakfast_time=meal_times[
            "breakfast"
        ],

        lunch_time=meal_times[
            "lunch"
        ],

        dinner_time=meal_times[
            "dinner"
        ],

        meal_times=meal_times
    )


# ============================================================
# LOG MEAL
# ============================================================

@app.route(
    "/log-meal",
    methods=["GET", "POST"]
)
def log_meal():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    pet = get_pet()

    if not pet:

        return redirect(
            url_for("pet_profile")
        )

    prescription = get_active_prescription(
        session["user_id"]
    )

    condition = "General"
    treatment_day = 0

    if prescription:

        condition = (
            prescription["condition"]
            or detect_health_condition(
                prescription[
                    "extracted_text"
                ]
            )
        )

        treatment_day = get_treatment_day(
            prescription
        )

    food_plan = create_food_plan(
        pet,
        condition
    )

    # --------------------------------------------------------
    # UPLOAD MEAL
    # --------------------------------------------------------

    if request.method == "POST":

        meal_type = request.form.get(
            "meal_type",
            "breakfast"
        )

        if meal_type not in [
            "breakfast",
            "lunch",
            "dinner"
        ]:

            meal_type = "breakfast"

        photo = request.files.get(
            "photo"
        )

        if not photo or photo.filename == "":

            flash(
                "Please upload a meal photo."
            )

            return redirect(
                url_for(
                    "log_meal",
                    meal_type=meal_type
                )
            )

        filename = secure_filename(
            photo.filename
        )

        if "." not in filename:

            flash(
                "Invalid image."
            )

            return redirect(
                url_for("log_meal")
            )

        extension = filename.rsplit(
            ".",
            1
        )[1].lower()

        if extension not in [
            "jpg",
            "jpeg",
            "png",
            "webp"
        ]:

            flash(
                "Please upload JPG, JPEG, PNG or WEBP."
            )

            return redirect(
                url_for("log_meal")
            )

        timestamp = datetime.now().strftime(
            "%Y%m%d%H%M%S%f"
        )

        filename = (
            timestamp
            + "_"
            + filename
        )

        photo_path = os.path.join(
            app.config["MEAL_FOLDER"],
            filename
        )

        photo.save(
            photo_path
        )

        if not verify_meal_photo(
            photo_path
        ):

            try:

                os.remove(
                    photo_path
                )

            except OSError:

                pass

            flash(
                "Please upload a clear photo of your pet's actual meal."
            )

            return redirect(
                url_for("log_meal")
            )

        meal_name = food_plan[
            meal_type
        ]["food"]

        meal_portion = food_plan[
            meal_type
        ]["portion"]

        meal_description = (
            f"{meal_name} | "
            f"Portion: {meal_portion}"
        )

        today = date.today().strftime(
            "%Y-%m-%d"
        )

        conn = get_db()

        existing = conn.execute(
            """
            SELECT id, photo
            FROM meals
            WHERE user_id = ?
            AND pet_id = ?
            AND meal_type = ?
            AND date = ?
            """,
            (
                session["user_id"],
                pet["id"],
                meal_type,
                today
            )
        ).fetchone()

        # ----------------------------------------------------
        # UPDATE EXISTING MEAL
        # ----------------------------------------------------

        if existing:

            old_photo = existing[
                "photo"
            ]

            conn.execute(
                """
                UPDATE meals
                SET
                    meal_name = ?,
                    photo = ?
                WHERE id = ?
                """,
                (
                    meal_description,
                    filename,
                    existing["id"]
                )
            )

            if old_photo:

                old_path = os.path.join(
                    app.config[
                        "MEAL_FOLDER"
                    ],
                    old_photo
                )

                if os.path.exists(
                    old_path
                ):

                    try:

                        os.remove(
                            old_path
                        )

                    except OSError:

                        pass

        # ----------------------------------------------------
        # INSERT NEW MEAL
        # ----------------------------------------------------

        else:

            conn.execute(
                """
                INSERT INTO meals
                (
                    user_id,
                    pet_id,
                    meal_type,
                    meal_name,
                    photo,
                    date
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session["user_id"],
                    pet["id"],
                    meal_type,
                    meal_description,
                    filename,
                    today
                )
            )

        conn.commit()
        conn.close()

        flash(
            f"{meal_type.capitalize()} meal uploaded successfully."
        )

        return redirect(
            url_for("streak")
        )

    # --------------------------------------------------------
    # DISPLAY LOG MEAL PAGE
    # --------------------------------------------------------

    selected_meal = request.args.get(
        "meal_type",
        "breakfast"
    )

    if selected_meal not in [
        "breakfast",
        "lunch",
        "dinner"
    ]:

        selected_meal = "breakfast"

    selected_plan = food_plan[
        selected_meal
    ]

    return render_template(
        "meal_upload.html",
        pet=pet,
        prescription=prescription,
        condition=condition,
        treatment_day=treatment_day,
        food_plan=food_plan,
        selected_meal=selected_meal,
        suggested_food=selected_plan[
            "food"
        ],
        suggested_portion=selected_plan[
            "portion"
        ],
        suggested_percentage=selected_plan[
            "percentage"
        ]
    )


# ============================================================
# STREAK
# ============================================================

@app.route("/streak")
def streak():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    current_streak = calculate_streak(
        user_id
    )

    longest_streak = calculate_longest_streak(
        user_id
    )

    conn = get_db()

    meal_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM meals
        WHERE user_id = ?
        """,
        (
            user_id,
        )
    ).fetchone()[0]

    today = date.today().strftime(
        "%Y-%m-%d"
    )

    today_meals = conn.execute(
        """
        SELECT DISTINCT meal_type
        FROM meals
        WHERE user_id = ?
        AND date = ?
        AND meal_type IN (
            'breakfast',
            'lunch',
            'dinner'
        )
        """,
        (
            user_id,
            today
        )
    ).fetchall()

    conn.close()

    completed = {
        row["meal_type"]
        for row in today_meals
    }

    breakfast_done = (
        "breakfast" in completed
    )

    lunch_done = (
        "lunch" in completed
    )

    dinner_done = (
        "dinner" in completed
    )

    today_complete = (
        breakfast_done
        and lunch_done
        and dinner_done
    )

    return render_template(
        "streak.html",
        current_streak=current_streak,
        longest_streak=longest_streak,
        meal_count=meal_count,
        breakfast_done=breakfast_done,
        lunch_done=lunch_done,
        dinner_done=dinner_done,
        today_complete=today_complete
    )


# ============================================================
# RESET STREAK
# ============================================================
#
# IMPORTANT:
#
# Streak is calculated from meal records.
# There is no separate "streak" table.
#
# Therefore deleting meal records resets the streak.
#
# ============================================================

@app.route(
    "/reset-streak",
    methods=["POST"]
)
def reset_streak():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    conn = get_db()

    meals = conn.execute(
        """
        SELECT photo
        FROM meals
        WHERE user_id = ?
        """,
        (
            session["user_id"],
        )
    ).fetchall()

    # Delete meal images.
    for meal in meals:

        photo = meal["photo"]

        if photo:

            filepath = os.path.join(
                app.config["MEAL_FOLDER"],
                photo
            )

            if os.path.exists(
                filepath
            ):

                try:

                    os.remove(
                        filepath
                    )

                except OSError:

                    pass

    # Delete meal records.
    conn.execute(
        """
        DELETE FROM meals
        WHERE user_id = ?
        """,
        (
            session["user_id"],
        )
    )

    conn.commit()
    conn.close()

    flash(
        "🔥 Your streak has been reset."
    )

    return redirect(
        url_for("streak")
    )


# ============================================================
# DELETE ONE MEAL
# ============================================================

@app.route(
    "/delete-meal/<int:meal_id>",
    methods=["POST"]
)
def delete_meal(meal_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    conn = get_db()

    meal = conn.execute(
        """
        SELECT *
        FROM meals
        WHERE id = ?
        AND user_id = ?
        """,
        (
            meal_id,
            session["user_id"]
        )
    ).fetchone()

    if not meal:

        conn.close()

        flash(
            "Meal not found."
        )

        return redirect(
            url_for("meal_history")
        )

    photo = meal["photo"]

    if photo:

        filepath = os.path.join(
            app.config["MEAL_FOLDER"],
            photo
        )

        if os.path.exists(
            filepath
        ):

            try:

                os.remove(
                    filepath
                )

            except OSError:

                pass

    conn.execute(
        """
        DELETE FROM meals
        WHERE id = ?
        AND user_id = ?
        """,
        (
            meal_id,
            session["user_id"]
        )
    )

    conn.commit()
    conn.close()

    flash(
        "🗑 Meal deleted successfully."
    )

    return redirect(
        url_for("meal_history")
    )


# ============================================================
# PROGRESS
# ============================================================

@app.route("/progress")
def progress():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    today = date.today().strftime(
        "%Y-%m-%d"
    )

    conn = get_db()

    total_meals = conn.execute(
        """
        SELECT COUNT(*)
        FROM meals
        WHERE user_id = ?
        """,
        (
            user_id,
        )
    ).fetchone()[0]

    today_meals = conn.execute(
        """
        SELECT COUNT(DISTINCT meal_type)
        FROM meals
        WHERE user_id = ?
        AND date = ?
        AND meal_type IN (
            'breakfast',
            'lunch',
            'dinner'
        )
        """,
        (
            user_id,
            today
        )
    ).fetchone()[0]

    conn.close()

    percentage = min(
        int(
            (today_meals / 3) * 100
        ),
        100
    )

    return render_template(
        "progress.html",
        total_meals=total_meals,
        today_meals=today_meals,
        percentage=percentage
    )


# ============================================================
# MEAL HISTORY
# ============================================================

@app.route("/meal-history")
def meal_history():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    conn = get_db()

    meals = conn.execute(
        """
        SELECT *
        FROM meals
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        """,
        (
            session["user_id"],
        )
    ).fetchall()

    conn.close()

    return render_template(
        "meal_history.html",
        meals=meals
    )


# ============================================================
# PROFILE
# ============================================================

@app.route("/profile")
def profile():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    conn = get_db()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (
            session["user_id"],
        )
    ).fetchone()

    conn.close()

    return render_template(
        "profile.html",
        user=user
    )


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def page_not_found(error):

    return render_template(
        "index.html"
    ), 404


@app.errorhandler(500)
def internal_server_error(error):

    return """
    <h2>Something went wrong.</h2>
    <p>
        Please check the Flask terminal
        for the exact error.
    </p>
    """, 500


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    start_notification_worker()

    print("")
    print("🐾 PET CARE APPLICATION")
    print("==============================")
    print("🥣 Breakfast notification : 08:00")
    print("🍚 Lunch notification     : 13:00")
    print("🍲 Dinner notification    : 20:00")
    print("==============================")

    app.run(
        debug=True,
        use_reloader=False
    )