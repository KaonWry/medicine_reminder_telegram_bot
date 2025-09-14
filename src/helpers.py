import sqlite3
import re
from telegram import Update
import os
import pathlib


ROOT_PATH = pathlib.Path(__file__).parent.parent.resolve()
DB_PATH = os.path.join(ROOT_PATH, "src", "reminders.db")


def is_valid_time_format(time_str):
    """
    Validate time string against HH:MM 24-hour format.
    Returns True if valid, False otherwise.
    """
    return bool(re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", time_str))


def get_user_data(context):
    """
    Safely get or initialize context.user_data as a dict.
    Used to store per-user state in conversation flows.
    """
    if not hasattr(context, "user_data") or context.user_data is None:
        context.user_data = {}
    return context.user_data


def get_user_id(update: Update):
    """
    Extract the Telegram user ID from an update object.
    Returns None if not available.
    """
    user = getattr(update, "effective_user", None)
    return getattr(user, "id", None)


def get_message_text(update):
    """
    Safely get the text from update.message, or None if not available.
    Used for extracting user input in conversation flows.
    """
    if (
        not update.message
        or not hasattr(update.message, "text")
        or update.message.text is None
    ):
        return None
    return update.message.text.strip()


def get_reminders_for_user(user_id: int):
    """
    Retrieve all reminders for a given user, sorted by time.
    Args:
        user_id (int): Telegram user ID
    Returns:
        list of (id, time, name) tuples
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, time, name FROM reminders WHERE user_id = ? ORDER BY time",
        (user_id,),
    )
    reminders = cursor.fetchall()
    conn.close()
    return reminders
