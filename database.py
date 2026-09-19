
import sqlite3
from datetime import datetime


# ============================================================
# DATABASE
# ============================================================

DATABASE = "pet_care.db"


# ============================================================
# CONNECTION
# ============================================================

def get_db():

    conn = sqlite3.connect(
        DATABASE
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn


# ============================================================
# ADD COLUMN IF MISSING
# ============================================================

def add_column_if_missing(
    cursor,
    table_name,
    column_name,
    column_definition
):

    columns = cursor.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    existing = {
        column["name"]
        for column in columns
    }

    if column_name not in existing:

        cursor.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name}
            {column_definition}
            """
        )


# ============================================================
# CREATE TABLES
# ============================================================

def create_tables():

    conn = get_db()

    cursor = conn.cursor()


    # ========================================================
    # USERS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL

        )
    """)


    # ========================================================
    # PETS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pets (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            name TEXT,

            pet_type TEXT,

            breed TEXT,

            age INTEGER,

            weight REAL,

            activity TEXT,

            food_preference TEXT,

            allergies TEXT,

            veterinarian TEXT,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE

        )
    """)


    # ========================================================
    # PRESCRIPTIONS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prescriptions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            pet_id INTEGER,

            filename TEXT,

            extracted_text TEXT,

            condition TEXT,

            uploaded_at TEXT,

            food_suggestions TEXT,

            status TEXT DEFAULT 'active',

            diagnosed_at TEXT,

            cured_at TEXT,

            treatment_start TEXT,

            ocr_confidence REAL,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            FOREIGN KEY (pet_id)
                REFERENCES pets(id)
                ON DELETE SET NULL

        )
    """)


    # ========================================================
    # MEALS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meals (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            pet_id INTEGER,

            meal_type TEXT,

            meal_name TEXT,

            photo TEXT,

            date TEXT,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            FOREIGN KEY (pet_id)
                REFERENCES pets(id)
                ON DELETE SET NULL

        )
    """)


    # ========================================================
    # MEAL NOTIFICATIONS
    #
    # One row per user/pet.
    #
    # Default times:
    # Breakfast = 08:00
    # Lunch     = 13:00
    # Dinner    = 19:00
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meal_notifications (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            pet_id INTEGER,

            breakfast_time TEXT DEFAULT '08:00',

            lunch_time TEXT DEFAULT '13:00',

            dinner_time TEXT DEFAULT '19:00',

            breakfast_enabled INTEGER DEFAULT 1,

            lunch_enabled INTEGER DEFAULT 1,

            dinner_enabled INTEGER DEFAULT 1,

            last_breakfast_notification TEXT,

            last_lunch_notification TEXT,

            last_dinner_notification TEXT,

            created_at TEXT,

            updated_at TEXT,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            FOREIGN KEY (pet_id)
                REFERENCES pets(id)
                ON DELETE CASCADE,

            UNIQUE(user_id, pet_id)

        )
    """)


    # ========================================================
    # PRESCRIPTION MIGRATIONS
    # ========================================================

    add_column_if_missing(
        cursor,
        "prescriptions",
        "condition",
        "TEXT"
    )

    add_column_if_missing(
        cursor,
        "prescriptions",
        "uploaded_at",
        "TEXT"
    )

    add_column_if_missing(
        cursor,
        "prescriptions",
        "food_suggestions",
        "TEXT"
    )

    add_column_if_missing(
        cursor,
        "prescriptions",
        "status",
        "TEXT DEFAULT 'Active'"
    )

    add_column_if_missing(
        cursor,
        "prescriptions",
        "diagnosed_at",
        "TEXT"
    )

    add_column_if_missing(
        cursor,
        "prescriptions",
        "cured_at",
        "TEXT"
    )

    add_column_if_missing(
        cursor,
        "prescriptions",
        "treatment_start",
        "TEXT"
    )

    add_column_if_missing(
        cursor,
        "prescriptions",
        "ocr_confidence",
        "REAL"
    )


    # ========================================================
    # MEAL MIGRATIONS
    # ========================================================

    add_column_if_missing(
        cursor,
        "meals",
        "meal_type",
        "TEXT"
    )

    add_column_if_missing(
        cursor,
        "meals",
        "meal_name",
        "TEXT"
    )

    add_column_if_missing(
        cursor,
        "meals",
        "photo",
        "TEXT"
    )

    add_column_if_missing(
        cursor,
        "meals",
        "date",
        "TEXT"
    )


    # ========================================================
    # NOTIFICATION MIGRATIONS
    # ========================================================

    add_column_if_missing(
        cursor,
        "meal_notifications",
        "breakfast_time",
        "TEXT DEFAULT '08:00'"
    )

    add_column_if_missing(
        cursor,
        "meal_notifications",
        "lunch_time",
        "TEXT DEFAULT '13:00'"
    )

    add_column_if_missing(
        cursor,
        "meal_notifications",
        "dinner_time",
        "TEXT DEFAULT '19:00'"
    )

    add_column_if_missing(
        cursor,
        "meal_notifications",
        "breakfast_enabled",
        "INTEGER DEFAULT 1"
    )

    add_column_if_missing(
        cursor,
        "meal_notifications",
        "lunch_enabled",
        "INTEGER DEFAULT 1"
    )

    add_column_if_missing(
        cursor,
        "meal_notifications",
        "dinner_enabled",
        "INTEGER DEFAULT 1"
    )

    add_column_if_missing(
        cursor,
        "meal_notifications",
        "last_breakfast_notification",
        "TEXT"
    )

    add_column_if_missing(
        cursor,
        "meal_notifications",
        "last_lunch_notification",
        "TEXT"
    )

    add_column_if_missing(
        cursor,
        "meal_notifications",
        "last_dinner_notification",
        "TEXT"
    )

    add_column_if_missing(
        cursor,
        "meal_notifications",
        "created_at",
        "TEXT"
    )

    add_column_if_missing(
        cursor,
        "meal_notifications",
        "updated_at",
        "TEXT"
    )


    # ========================================================
    # INDEXES
    # ========================================================

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_prescriptions_user
        ON prescriptions(user_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_prescriptions_pet
        ON prescriptions(pet_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_prescriptions_status
        ON prescriptions(status)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_meals_user
        ON meals(user_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_meals_date
        ON meals(date)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_notifications_user
        ON meal_notifications(user_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_notifications_pet
        ON meal_notifications(pet_id)
    """)


    # ========================================================
    # NORMALIZE OLD STATUS
    # ========================================================

    cursor.execute("""
        UPDATE prescriptions
        SET status = 'Active'
        WHERE status IS NULL
        OR TRIM(status) = ''
    """)

    cursor.execute("""
        UPDATE prescriptions
        SET status = 'Active'
        WHERE LOWER(TRIM(status)) = 'active'
    """)

    cursor.execute("""
        UPDATE prescriptions
        SET status = 'Cured'
        WHERE LOWER(TRIM(status)) = 'cured'
    """)


    # ========================================================
    # FIX DATES
    # ========================================================

    cursor.execute("""
        UPDATE prescriptions
        SET treatment_start = uploaded_at
        WHERE (
            treatment_start IS NULL
            OR TRIM(treatment_start) = ''
        )
        AND uploaded_at IS NOT NULL
        AND TRIM(uploaded_at) != ''
    """)

    cursor.execute("""
        UPDATE prescriptions
        SET diagnosed_at = uploaded_at
        WHERE diagnosed_at IS NULL
        AND uploaded_at IS NOT NULL
    """)


    conn.commit()

    conn.close()


# ============================================================
# ACTIVE PRESCRIPTION
# ============================================================

def get_active_prescription(
    user_id,
    pet_id=None
):

    conn = get_db()

    if pet_id is not None:

        row = conn.execute(
            """
            SELECT *
            FROM prescriptions

            WHERE user_id = ?
            AND pet_id = ?
            AND LOWER(TRIM(status)) = 'active'

            ORDER BY id DESC
            LIMIT 1
            """,
            (
                user_id,
                pet_id
            )
        ).fetchone()

    else:

        row = conn.execute(
            """
            SELECT *
            FROM prescriptions

            WHERE user_id = ?
            AND LOWER(TRIM(status)) = 'active'

            ORDER BY id DESC
            LIMIT 1
            """,
            (
                user_id,
            )
        ).fetchone()

    conn.close()

    return row


# ============================================================
# LATEST PRESCRIPTION
# ============================================================

def get_latest_prescription(
    user_id,
    pet_id=None
):

    conn = get_db()

    if pet_id is not None:

        row = conn.execute(
            """
            SELECT *
            FROM prescriptions

            WHERE user_id = ?
            AND pet_id = ?

            ORDER BY id DESC
            LIMIT 1
            """,
            (
                user_id,
                pet_id
            )
        ).fetchone()

    else:

        row = conn.execute(
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

    return row


# ============================================================
# PRESCRIPTION HISTORY
# ============================================================

def get_prescription_history(
    user_id,
    pet_id=None
):

    conn = get_db()

    if pet_id is not None:

        rows = conn.execute(
            """
            SELECT *
            FROM prescriptions

            WHERE user_id = ?
            AND pet_id = ?

            ORDER BY id DESC
            """,
            (
                user_id,
                pet_id
            )
        ).fetchall()

    else:

        rows = conn.execute(
            """
            SELECT *
            FROM prescriptions

            WHERE user_id = ?

            ORDER BY id DESC
            """,
            (
                user_id,
            )
        ).fetchall()

    conn.close()

    return rows


# ============================================================
# SAVE PRESCRIPTION
# ============================================================

def save_prescription(
    user_id,
    pet_id,
    filename,
    extracted_text,
    condition,
    food_suggestions,
    ocr_confidence=0.0
):

    conn = get_db()

    now = datetime.now()

    uploaded_at = now.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    treatment_start = now.strftime(
        "%Y-%m-%d"
    )

    if isinstance(
        food_suggestions,
        list
    ):

        food_text = "\n".join(
            food_suggestions
        )

    else:

        food_text = str(
            food_suggestions or ""
        )

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
            treatment_start,
            ocr_confidence
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            pet_id,
            filename,
            extracted_text,
            condition,
            uploaded_at,
            food_text,
            "Active",
            uploaded_at,
            treatment_start,
            ocr_confidence
        )
    )

    prescription_id = cursor.lastrowid

    conn.commit()

    conn.close()

    return prescription_id


# ============================================================
# UPDATE FOOD SUGGESTIONS
# ============================================================

def save_food_suggestions(
    prescription_id,
    user_id,
    suggestions
):

    if isinstance(
        suggestions,
        list
    ):

        suggestions = "\n".join(
            suggestions
        )

    conn = get_db()

    conn.execute(
        """
        UPDATE prescriptions

        SET food_suggestions = ?

        WHERE id = ?
        AND user_id = ?
        """,
        (
            str(suggestions),
            prescription_id,
            user_id
        )
    )

    conn.commit()

    conn.close()


# ============================================================
# MARK CURED
# ============================================================

def mark_prescription_cured(
    prescription_id,
    user_id
):

    conn = get_db()

    cured_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    cursor = conn.execute(
        """
        UPDATE prescriptions

        SET
            status = 'cured',
            cured_at = ?

        WHERE id = ?
        AND user_id = ?
        """,
        (
            cured_time,
            prescription_id,
            user_id
        )
    )

    conn.commit()

    success = (
        cursor.rowcount > 0
    )

    conn.close()

    return success


# ============================================================
# REACTIVATE
# ============================================================

def reactivate_prescription(
    prescription_id,
    user_id
):

    conn = get_db()

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    conn.execute(
        """
        UPDATE prescriptions

        SET
            status = 'Active',
            cured_at = NULL,
            treatment_start = ?

        WHERE id = ?
        AND user_id = ?
        """,
        (
            today,
            prescription_id,
            user_id
        )
    )

    conn.commit()

    conn.close()


# ============================================================
# CREATE DEFAULT MEAL NOTIFICATIONS
# ============================================================

def create_meal_notifications(
    user_id,
    pet_id
):

    conn = get_db()

    now = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    existing = conn.execute(
        """
        SELECT id
        FROM meal_notifications

        WHERE user_id = ?
        AND pet_id = ?
        """,
        (
            user_id,
            pet_id
        )
    ).fetchone()


    if not existing:

        conn.execute(
            """
            INSERT INTO meal_notifications
            (
                user_id,
                pet_id,

                breakfast_time,
                lunch_time,
                dinner_time,

                breakfast_enabled,
                lunch_enabled,
                dinner_enabled,

                created_at,
                updated_at
            )

            VALUES (
                ?, ?,
                '08:00',
                '13:00',
                '19:00',
                1,
                1,
                1,
                ?,
                ?
            )
            """,
            (
                user_id,
                pet_id,
                now,
                now
            )
        )


    conn.commit()

    conn.close()


# ============================================================
# GET MEAL NOTIFICATIONS
# ============================================================

def get_meal_notifications(
    user_id,
    pet_id
):

    create_meal_notifications(
        user_id,
        pet_id
    )

    conn = get_db()

    settings = conn.execute(
        """
        SELECT *
        FROM meal_notifications

        WHERE user_id = ?
        AND pet_id = ?

        LIMIT 1
        """,
        (
            user_id,
            pet_id
        )
    ).fetchone()

    conn.close()

    return settings


# ============================================================
# UPDATE MEAL NOTIFICATIONS
# ============================================================

def update_meal_notifications(
    user_id,
    pet_id,
    breakfast_time,
    lunch_time,
    dinner_time,
    breakfast_enabled,
    lunch_enabled,
    dinner_enabled
):

    create_meal_notifications(
        user_id,
        pet_id
    )

    now = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    conn = get_db()

    conn.execute(
        """
        UPDATE meal_notifications

        SET

            breakfast_time = ?,
            lunch_time = ?,
            dinner_time = ?,

            breakfast_enabled = ?,
            lunch_enabled = ?,
            dinner_enabled = ?,

            updated_at = ?

        WHERE user_id = ?
        AND pet_id = ?
        """,
        (
            breakfast_time,
            lunch_time,
            dinner_time,

            int(breakfast_enabled),
            int(lunch_enabled),
            int(dinner_enabled),

            now,

            user_id,
            pet_id
        )
    )

    conn.commit()

    conn.close()


# ============================================================
# CHECK WHICH MEAL NOTIFICATION IS DUE
# ============================================================

def get_due_meal_notifications(
    user_id,
    pet_id
):

    settings = get_meal_notifications(
        user_id,
        pet_id
    )

    if not settings:
        return []

    now = datetime.now()

    current_time = now.strftime(
        "%H:%M"
    )

    today = now.strftime(
        "%Y-%m-%d"
    )

    due = []

    meals = [

        (
            "breakfast",
            settings["breakfast_time"],
            settings["breakfast_enabled"],
            settings["last_breakfast_notification"]
        ),

        (
            "lunch",
            settings["lunch_time"],
            settings["lunch_enabled"],
            settings["last_lunch_notification"]
        ),

        (
            "dinner",
            settings["dinner_time"],
            settings["dinner_enabled"],
            settings["last_dinner_notification"]
        )
    ]


    for (
        meal_type,
        meal_time,
        enabled,
        last_notification
    ) in meals:

        if not enabled:
            continue

        if not meal_time:
            continue

        if current_time < meal_time:
            continue

        if last_notification == today:
            continue

        due.append(
            meal_type
        )


    return due


# ============================================================
# MARK NOTIFICATION AS SENT
# ============================================================

def mark_meal_notification_sent(
    user_id,
    pet_id,
    meal_type
):

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    conn = get_db()

    if meal_type == "breakfast":

        conn.execute(
            """
            UPDATE meal_notifications

            SET
                last_breakfast_notification = ?,
                updated_at = ?

            WHERE user_id = ?
            AND pet_id = ?
            """,
            (
                today,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                user_id,
                pet_id
            )
        )


    elif meal_type == "lunch":

        conn.execute(
            """
            UPDATE meal_notifications

            SET
                last_lunch_notification = ?,
                updated_at = ?

            WHERE user_id = ?
            AND pet_id = ?
            """,
            (
                today,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                user_id,
                pet_id
            )
        )


    elif meal_type == "dinner":

        conn.execute(
            """
            UPDATE meal_notifications

            SET
                last_dinner_notification = ?,
                updated_at = ?

            WHERE user_id = ?
            AND pet_id = ?
            """,
            (
                today,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                user_id,
                pet_id
            )
        )


    conn.commit()

    conn.close()


# ============================================================
# RESET TODAY'S NOTIFICATIONS
# Useful for testing
# ============================================================

def reset_meal_notifications(
    user_id,
    pet_id
):

    conn = get_db()

    conn.execute(
        """
        UPDATE meal_notifications

        SET
            last_breakfast_notification = NULL,
            last_lunch_notification = NULL,
            last_dinner_notification = NULL,
            updated_at = ?

        WHERE user_id = ?
        AND pet_id = ?
        """,
        (
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            user_id,
            pet_id
        )
    )

    conn.commit()

    conn.close()


# ============================================================
# GET TODAY'S MEALS
# ============================================================

def get_today_meals(
    user_id,
    pet_id=None
):

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    conn = get_db()

    if pet_id is not None:

        rows = conn.execute(
            """
            SELECT *
            FROM meals

            WHERE user_id = ?
            AND pet_id = ?
            AND date = ?

            ORDER BY id DESC
            """,
            (
                user_id,
                pet_id,
                today
            )
        ).fetchall()

    else:

        rows = conn.execute(
            """
            SELECT *
            FROM meals

            WHERE user_id = ?
            AND date = ?

            ORDER BY id DESC
            """,
            (
                user_id,
                today
            )
        ).fetchall()

    conn.close()

    return rows


# ============================================================
# INITIALIZE DATABASE
# ============================================================

if __name__ == "__main__":

    create_tables()

    print(
        "Database created/updated successfully."
    )

