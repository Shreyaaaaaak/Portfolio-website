import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path


CATEGORY_CHOICES = [
    "Health",
    "Learning",
    "Work",
    "Mindset",
    "Finance",
    "Personal",
]

DEFAULT_DB_PATH = Path(__file__).parent / "data" / "habits.db"
DB_PATH = Path(os.environ.get("HABIT_TRACKER_DB", str(DEFAULT_DB_PATH)))


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def ensure_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            target_days INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL,
            completed_on TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_checkins_habit_day
        ON checkins (habit_id, completed_on)
        """
    )

    connection.commit()
    connection.close()


def create_habit(name, category, target_days):
    clean_name = name.strip()
    clean_category = category.strip() or "General"

    if not clean_name:
        raise ValueError("Give the habit a name.")

    if len(clean_name) > 80:
        raise ValueError("Habit names should stay under 80 characters.")

    try:
        target_value = int(target_days)
    except (TypeError, ValueError):
        raise ValueError("Choose a weekly target between 1 and 7 days.") from None

    if not 1 <= target_value <= 7:
        raise ValueError("Choose a weekly target between 1 and 7 days.")

    connection = get_connection()
    connection.execute(
        """
        INSERT INTO habits (name, category, target_days)
        VALUES (?, ?, ?)
        """,
        (clean_name, clean_category, target_value),
    )
    connection.commit()
    connection.close()


def delete_habit(habit_id):
    connection = get_connection()
    connection.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
    connection.commit()
    connection.close()


def mark_habit_complete(habit_id, completed_on=None):
    completed_day = completed_on or date.today().isoformat()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO checkins (habit_id, completed_on)
        VALUES (?, ?)
        """,
        (habit_id, completed_day),
    )
    connection.commit()
    created = cursor.rowcount > 0
    connection.close()
    return created


def get_dashboard_data():
    connection = get_connection()
    cursor = connection.cursor()

    habit_rows = cursor.execute(
        """
        SELECT id, name, category, target_days, created_at
        FROM habits
        ORDER BY created_at DESC, id DESC
        """
    ).fetchall()

    habits = []
    for row in habit_rows:
        checkin_rows = cursor.execute(
            """
            SELECT completed_on
            FROM checkins
            WHERE habit_id = ?
            ORDER BY completed_on DESC
            """,
            (row["id"],),
        ).fetchall()

        completed_days = [date.fromisoformat(entry["completed_on"]) for entry in checkin_rows]
        week_count = count_last_seven_days(completed_days)
        progress_percent = int(min(100, round((week_count / row["target_days"]) * 100)))

        habits.append(
            {
                "id": row["id"],
                "name": row["name"],
                "category": row["category"],
                "target_days": row["target_days"],
                "completed_today": date.today() in set(completed_days),
                "current_streak": calculate_current_streak(completed_days),
                "longest_streak": calculate_longest_streak(completed_days),
                "week_count": week_count,
                "progress_percent": progress_percent,
                "target_message": build_target_message(week_count, row["target_days"]),
                "last_checkin": format_last_checkin(completed_days),
                "week_cells": build_week_cells(completed_days),
            }
        )

    connection.close()
    return {
        "summary": build_summary(habits),
        "habits": habits,
        "focus_habits": habits[:3],
    }


def calculate_current_streak(completed_days):
    completed_lookup = set(completed_days)
    streak = 0
    cursor_day = date.today()

    if cursor_day not in completed_lookup:
        cursor_day -= timedelta(days=1)

    while cursor_day in completed_lookup:
        streak += 1
        cursor_day -= timedelta(days=1)

    return streak


def calculate_longest_streak(completed_days):
    ordered_days = sorted(set(completed_days))
    if not ordered_days:
        return 0

    longest = 1
    current = 1

    for previous_day, current_day in zip(ordered_days, ordered_days[1:]):
        if current_day - previous_day == timedelta(days=1):
            current += 1
            longest = max(longest, current)
        else:
            current = 1

    return longest


def count_last_seven_days(completed_days):
    cutoff = date.today() - timedelta(days=6)
    return sum(1 for completed_day in set(completed_days) if completed_day >= cutoff)


def build_week_cells(completed_days):
    completed_lookup = set(completed_days)
    days = []

    for offset in range(6, -1, -1):
        current_day = date.today() - timedelta(days=offset)
        days.append(
            {
                "label": current_day.strftime("%a")[0],
                "date_label": current_day.strftime("%d %b"),
                "completed": current_day in completed_lookup,
            }
        )

    return days


def format_last_checkin(completed_days):
    if not completed_days:
        return "No check-ins yet"

    latest_day = max(completed_days)
    return latest_day.strftime("%d %b %Y")


def build_target_message(week_count, target_days):
    if week_count >= target_days:
        return "Target reached for this week."

    remaining_days = target_days - week_count
    suffix = "day" if remaining_days == 1 else "days"
    return f"{remaining_days} more {suffix} to hit the weekly target."


def build_summary(habits):
    total_habits = len(habits)
    checked_in_today = sum(1 for habit in habits if habit["completed_today"])
    active_streaks = sum(1 for habit in habits if habit["current_streak"] > 0)
    weekly_checkins = sum(habit["week_count"] for habit in habits)
    best_habit = max(habits, key=lambda habit: habit["current_streak"], default=None)

    return {
        "total_habits": total_habits,
        "checked_in_today": checked_in_today,
        "active_streaks": active_streaks,
        "weekly_checkins": weekly_checkins,
        "best_habit_name": best_habit["name"] if best_habit else "Add your first habit",
        "best_habit_streak": best_habit["current_streak"] if best_habit else 0,
    }
