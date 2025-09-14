import logging  # For logging bot activity
import os  # For file path and environment variable access
import sqlite3  # For SQLite database operations
import re  # For regex validation of reminder time
import pathlib # For project root path
from dotenv import load_dotenv  # For loading environment variables from .env
from telegram import Update  # Telegram update object
from apscheduler.schedulers.background import BackgroundScheduler  # For scheduled jobs
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)  # Bot framework

# Path to SQLite DB
PROJECT_ROOT = pathlib.Path(__file__).parent.parent.resolve()
DB_PATH = os.path.join(PROJECT_ROOT, "src", "reminders.db")

# States for ConversationHandler
ADD_TIME, ADD_NAME = range(2)
DELETE_CHOOSE = 0

# Environment and Logging
load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, ".env"))  # Load environment variables from .env in project root
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Telegram bot token
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Helper Functions
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


def reset_reminders_triggered():
    """
    Reset the triggered_today flag for all reminders to 0 in the database.
    Called daily by APScheduler to allow reminders to trigger again.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE reminders SET triggered_today = 0")
    conn.commit()
    conn.close()


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

# Conversation Handlers
async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Conversation entry for /add (no arguments).
    Prompts user for reminder time.
    """
    if not update.message:
        return ConversationHandler.END
    await update.message.reply_text(
        "Please type the time you want to be reminded in (HH:MM, 24-hour format):"
    )
    return ADD_TIME


async def add_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Conversation step for /add: receives time, validates format, prompts for name.
    """
    time = get_message_text(update)
    if time is None:
        return ConversationHandler.END
    if not is_valid_time_format(time):
        if update.message:
            await update.message.reply_text(
                "Invalid time format. Please type the time in HH:MM (24-hour format):"
            )
        return ADD_TIME
    user_data = get_user_data(context)
    user_data["add_time"] = time
    if update.message:
        await update.message.reply_text("What is the reminder about?")
    return ADD_NAME


async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Conversation step for /add: receives reminder name, validates, adds to DB.
    """
    name = get_message_text(update)
    if name is None:
        return ConversationHandler.END
    user_data = get_user_data(context)
    time = user_data.get("add_time")
    user_id = get_user_id(update)
    if not name:
        if update.message:
            await update.message.reply_text(
                "Reminder name cannot be empty. Please type the reminder:"
            )
        return ADD_NAME
    if user_id is None or time is None:
        if update.message:
            await update.message.reply_text("Could not determine user id or time.")
        return ConversationHandler.END
    context.args = [time, name]
    await add_reminder_to_db(update, context)
    return ConversationHandler.END


async def add_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Conversation fallback for /add: cancels reminder creation.
    """
    if update.message:
        await update.message.reply_text("Reminder creation cancelled.")
    return ConversationHandler.END


async def delete_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Conversation entry for /delete (no arguments).
    Prompts user to choose a reminder to delete.
    """
    user_id = get_user_id(update)
    if user_id is None:
        if update.message:
            await update.message.reply_text("Could not determine user id.")
        return ConversationHandler.END
    reminders = get_reminders_for_user(user_id)
    if not reminders:
        if update.message:
            await update.message.reply_text("You have no reminders set.")
        return ConversationHandler.END
    msg_lines = ["Your reminders:"]
    for idx, (rem_id, t, n) in enumerate(reminders, 1):
        msg_lines.append(f"{idx}. {t} - {n}")
    msg_lines.append("\nPlease type the number of the reminder you want to delete:")
    msg = "\n".join(msg_lines)
    user_data = get_user_data(context)
    user_data["reminders"] = reminders
    if update.message:
        await update.message.reply_text(msg)
    return DELETE_CHOOSE


async def delete_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Conversation step for /delete: receives reminder number, deletes from DB.
    """
    user_id = get_user_id(update)
    user_data = get_user_data(context)
    reminders = user_data.get("reminders", [])
    text = get_message_text(update)
    if text is None:
        return ConversationHandler.END
    if not text.isdigit():
        if update.message:
            await update.message.reply_text("Please type a valid number.")
        return DELETE_CHOOSE
    idx = int(text)
    if idx < 1 or idx > len(reminders):
        if update.message:
            await update.message.reply_text(
                f"Invalid number. You have {len(reminders)} reminders."
            )
        return DELETE_CHOOSE
    rem_id, t, n = reminders[idx - 1]
    if user_id is None:
        if update.message:
            await update.message.reply_text("Could not determine user id.")
        return ConversationHandler.END
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM reminders WHERE id = ? AND user_id = ?", (rem_id, user_id)
    )
    conn.commit()
    conn.close()
    if update.message:
        await update.message.reply_text(f"Deleted reminder {idx}: {t} - {n}")
    logging.info(f"User {user_id} deleted reminder {idx}: '{n}' at {t}")
    return ConversationHandler.END


async def delete_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Conversation fallback for /delete: cancels reminder deletion.
    """
    if update.message:
        await update.message.reply_text("Reminder deletion cancelled.")
    return ConversationHandler.END

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Telegram command handler for /start.
    Sends onboarding instructions to the user.
    """
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id:
        msg = (
            "Welcome to the Medicine Reminder Bot!\n\n"
            "Available commands:\n"
            "/add <reminder time> <reminder name> - Add a new reminder.\n"
            "    Example: /add 20:00 Medicine\n"
            "/list - List all your reminders, numbered for deletion.\n"
            "/delete <number> - Delete a reminder by its number from /list.\n"
            "    Example: /delete 1\n"
            "\nThe bot will store your reminders and notify you at the specified time."
        )
        await context.bot.send_message(chat_id=chat_id, text=msg)


async def add_reminder_to_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Telegram command handler for /add <reminder time> <reminder name>.
    Validates input, checks for duplicates, inserts reminder in DB.
    """
    args = context.args if context.args else []
    if len(args) < 2 or not update.message:
        if update.message:
            await update.message.reply_text(
                "Usage: /add <reminder time> <reminder name>"
            )
        return
    time = args[0]
    name = " ".join(args[1:])  # All text after time is the reminder name
    if not is_valid_time_format(time) or not name.strip():
        await update.message.reply_text(
            "Invalid format. Usage: /add <reminder time> <reminder name>\nExample: /add 20:00 Medicine"
        )
        return
    user_id = get_user_id(update)
    if user_id is None:
        await update.message.reply_text("Could not determine user id.")
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM reminders WHERE user_id = ? AND name = ?",
        (user_id, name),
    )
    if cursor.fetchone():
        conn.close()
        await update.message.reply_text(
            f"You already have a reminder named '{name}'. Please choose a different name."
        )
        return
    cursor.execute(
        "INSERT INTO reminders (user_id, time, name) VALUES (?, ?, ?)",
        (user_id, time, name),
    )
    conn.commit()
    conn.close()
    logging.info(f"User {user_id} added reminder: '{name}' at {time}")
    await update.message.reply_text(f'Ok, I\'ll remind you at {time} for "{name}".')
    return


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


async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Telegram command handler for /list.
    Lists all reminders for the requesting user, numbered for deletion.
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


async def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Telegram command handler for /delete <number>.
    Deletes the user's reminder at the given index.
    """
    user_id = get_user_id(update)
    if user_id is None or not update.message:
        if update.message:
            await update.message.reply_text("Could not determine user id.")
        return
    args = context.args if context.args else []
    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text(
            "Usage: /delete <number>\nUse /list to see reminder numbers."
        )
        return
    idx = int(args[0])
    reminders = get_reminders_for_user(user_id)
    if idx < 1 or idx > len(reminders):
        await update.message.reply_text(
            f"Invalid number. You have {len(reminders)} reminders."
        )
        return
    rem_id, t, n = reminders[idx - 1]
    # Delete from DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM reminders WHERE id = ? AND user_id = ?", (rem_id, user_id)
    )
    conn.commit()
    conn.close()
    await update.message.reply_text(f"Deleted reminder {idx}: {t} - {n}")
    logging.info(f"User {user_id} deleted reminder {idx}: '{n}' at {t}")


if __name__ == "__main__":
    # Check for BOT_TOKEN
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN not set in environment.")
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register command handlers
    start_handler = CommandHandler("start", start)
    list_handler = CommandHandler("list", list_reminders)

    # Conversation handlers for /add and /delete accessibility
    add_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("add", add_start, filters=filters.Regex(r"^/add$"))
        ],
        states={
            ADD_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_time)],
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
        },
        fallbacks=[CommandHandler("cancel", add_cancel)],
    )
    delete_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("delete", delete_start, filters=filters.Regex(r"^/delete$"))
        ],
        states={
            DELETE_CHOOSE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_choose)
            ],
        },
        fallbacks=[CommandHandler("cancel", delete_cancel)],
    )

    # Register ConversationHandlers BEFORE regular CommandHandlers for /add and /delete
    application.add_handler(add_conv_handler)
    application.add_handler(delete_conv_handler)
    application.add_handler(start_handler)
    application.add_handler(list_handler)
    application.add_handler(
        CommandHandler("add", add_reminder_to_db, filters=filters.Regex(r"^/add .+"))
    )
    application.add_handler(
        CommandHandler("delete", delete_reminder, filters=filters.Regex(r"^/delete .+"))
    )

    # Schedule daily reset of triggered_today at midnight
    scheduler = BackgroundScheduler()
    scheduler.add_job(reset_reminders_triggered, "cron", hour=0, minute=0)
    scheduler.start()

    application.run_polling()  # Start polling for updates
