import sqlite3
from datetime import datetime, timezone, timedelta
import logging
from helpers import DB_PATH
import asyncio


def reset_reminders_triggered():
    """
    Reset the triggered_today flag for all reminders to 0 in the database.
    Called daily by APScheduler to allow reminders to trigger again.
    Args:
        None
    Returns:
        None
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE reminders SET triggered_today = 0")
    conn.commit()
    conn.close()


def reset_reminder(tz_offset=7):
    """Reset reminders at local midnight.
    Args:
        tz_offset (int): timezone offset in hours (default 7 for UTC+7)
    Returns:
        None
    """
    tz = timezone(timedelta(hours=tz_offset))
    now_utc = datetime.now(timezone.utc)
    local_time = now_utc.astimezone(tz)
    # Only run at local midnight
    if local_time.hour == 0 and local_time.minute == 0:
        reset_reminders_triggered()


def get_due_reminders(tz_offset=7):
    """
    Check the database for reminders due at or before the current local time and update their triggered_today flag.
    Returns a list of (user_id, name, time) for reminders due now or missed during downtime.
    Args:
        tz_offset (int): timezone offset in hours (default 7 for UTC+7)
    Returns:
        list of (user_id, name, time) tuples for due reminders
    """
    now_utc = datetime.now(timezone.utc)
    tz = timezone(timedelta(hours=tz_offset))
    local_time = now_utc.astimezone(tz)
    current_time_str = local_time.strftime("%H:%M")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Select reminders where time <= current_time_str and not triggered today
    cursor.execute(
        "SELECT id, user_id, name, time FROM reminders WHERE time <= ? AND triggered_today = 0",
        (current_time_str,),
    )
    due_reminders = cursor.fetchall()
    # Mark these reminders as triggered
    for rem_id, user_id, name, time in due_reminders:
        cursor.execute(
            "UPDATE reminders SET triggered_today = 1 WHERE id = ?", (rem_id,)
        )
    conn.commit()
    conn.close()
    return [(user_id, name, time) for _, user_id, name, time in due_reminders]


async def poll_due_reminders(application, tz_offset=7):
    """
    Poll for due reminders and send messages to users.
    Args:
        application: Telegram application object
        tz_offset (int): timezone offset in hours (default 7 for UTC+7)
    Returns:
        None
    """
    due = get_due_reminders(tz_offset)
    for user_id, name, time in due:
        try:
            await application.bot.send_message(
                chat_id=user_id, text=f"You have a reminder for '{name}' at {time}."
            )
        except Exception as e:
            logging.error(f"Failed to send reminder to user {user_id}: {e}")


def scheduled_job(application):
    reset_reminder()
    due = get_due_reminders()

    async def send_all():
        for user_id, name, time in due:
            try:
                await application.bot.send_message(
                    chat_id=user_id,
                    text=f"You have a reminder for '{name}' at {time}.",
                )
            except Exception as e:
                logging.error(f"Failed to send reminder to user {user_id}: {e}")

    if due:
        asyncio.run(send_all())
