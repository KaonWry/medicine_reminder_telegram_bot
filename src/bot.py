import logging  # For logging bot activity
import os  # For file path and environment variable access
import sqlite3  # For SQLite database operations
from dotenv import load_dotenv  # For loading environment variables from .env
from datetime import datetime, timedelta, timezone  # Time handling
from apscheduler.schedulers.background import BackgroundScheduler  # For scheduled jobs

# Bot framework
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    filters,
)

# Helper functions
from helpers import (
    get_user_id,
    get_reminders_for_user,
    ROOT_PATH,
    DB_PATH,
)

# /add command handler
from add import (
    add_reminder_to_db,
    add_conv_handler,
)

# /delete command handler
from delete import (
    delete_reminder,
    delete_conv_handler,
)


# Environment and Logging
load_dotenv(
    dotenv_path=os.path.join(ROOT_PATH, ".env")
)  # Load environment variables from .env in project root
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Telegram bot token
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


# Helper Functions
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


# Command Handlers
# /start
async def start(update, context):
    """
    Telegram command handler for /start.
    Sends onboarding instructions to the user.
    Args:
        update: Telegram update object
        context: Telegram context object
    Returns:
        None
    """
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id:
        msg = (
            "Welcome to the Medicine Reminder Bot!\n\n"
            "Available commands:\n"
            "/start - Show this help message.\n"
            "/add <reminder time> <reminder name> - Add a new reminder.\n"
            "    Example: /add 20:00 Medicine\n"
            "/list - List all your reminders, numbered for deletion.\n"
            "/delete <number> - Delete a reminder by its number from /list.\n"
            "    Example: /delete 1\n"
            "\nThe bot will store your reminders and notify you at the specified time."
        )
        await context.bot.send_message(chat_id=chat_id, text=msg)


# /list
async def list_reminders(update, context):
    """
    Telegram command handler for /list.
    Lists all reminders for the requesting user, numbered for deletion.
    Args:
        update: Telegram update object
        context: Telegram context object
    Returns:
        None
    """
    user_id = get_user_id(update)
    if user_id is None or not update.message:
        if update.message:
            await update.message.reply_text("Could not determine user id.")
        return
    reminders = get_reminders_for_user(user_id)
    if not reminders:
        await update.message.reply_text("You have no reminders set.")
        return
    msg_lines = ["Your reminders:"]
    for idx, (rem_id, t, n) in enumerate(reminders, 1):
        msg_lines.append(f"{idx}. {t} - {n}")
    msg = "\n".join(msg_lines)
    await update.message.reply_text(msg)


# Reminder due check and notification
def get_due_reminders(tz_offset=7):
    """
    Check the database for reminders due at or before the current local time and update their triggered_today flag.
    Returns a list of (user_id, name, time) for reminders due now or missed during downtime.
    Args:
        tz_offset (int): timezone offset in hours (default 7 for UTC+7)
    Returns:
        list of (user_id, name, time) tuples for due reminders
    """
    from datetime import datetime, timezone, timedelta

    now_utc = datetime.now(timezone.utc)
    tz = timezone(timedelta(hours=tz_offset))
    local_time = now_utc.astimezone(tz)
    current_time_str = local_time.strftime("%H:%M")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Select reminders where time <= current_time_str and not triggered today
    cursor.execute(
        "SELECT id, user_id, name, time FROM reminders WHERE time <= ? AND triggered_today = 0",
        (current_time_str,)
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


if __name__ == "__main__":
    # Check for BOT_TOKEN
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN not set in environment.")
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register command handlers
    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)
    list_handler = CommandHandler("list", list_reminders)
    application.add_handler(list_handler)
    application.add_handler(add_conv_handler)
    application.add_handler(delete_conv_handler)
    application.add_handler(
        CommandHandler("add", add_reminder_to_db, filters=filters.Regex(r"^/add .+"))
    )
    application.add_handler(
        CommandHandler("delete", delete_reminder, filters=filters.Regex(r"^/delete .+"))
    )

    # Schedule a single job to check both midnight reset and due reminders every minute
    def scheduled_job():
        reset_reminder()  # Will only reset at local midnight
        due = get_due_reminders()
        import asyncio

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

    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_job, "cron", minute="*")
    scheduler.start()

    # Start the bot
    application.run_polling()
