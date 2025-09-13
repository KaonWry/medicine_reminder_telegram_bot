import logging  # For logging bot activity
import os  # For file path and environment variable access
import sqlite3  # For SQLite database operations
import re  # For regex validation of reminder time
from dotenv import load_dotenv  # For loading environment variables from .env
from telegram import Update  # Telegram update object
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
)  # Bot framework

DB_PATH = os.path.join(os.path.dirname(__file__), "reminders.db")  # Path to SQLite DB


def add_reminder_to_db(user_id: int, time: str, name: str):
    """
    Add a reminder to the database for a specific user.
    Args:
        user_id (int): Telegram user ID
        time (str): Reminder time in HH:MM format
        name (str): Reminder name
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reminders (user_id, time, name) VALUES (?, ?, ?)",
        (user_id, time, name),
    )
    conn.commit()
    conn.close()


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
    user_id = (
        update.effective_user.id
        if update.effective_user and hasattr(update.effective_user, "id")
        else None
    )
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
    user_id = (
        update.effective_user.id
        if update.effective_user and hasattr(update.effective_user, "id")
        else None
    )
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


load_dotenv()  # Load environment variables from .env file
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Telegram bot token
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)  # Set up logging


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Telegram command handler for /start.
    Sends onboarding instructions to the user.
    """
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id:
        msg = (
            "Welcome to the Medicine Reminder Bot!\n"
            "Use /add <reminder time> <reminder name> to set a reminder.\n"
            "Example: /add 20:00 Medicine\n"
            "The bot will store your reminders and notify you at the specified time."
        )
        await context.bot.send_message(chat_id=chat_id, text=msg)


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Telegram command handler for /add.
    Adds a new reminder for the user if the format is valid.
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
    # Regex: HH:MM (24-hour) and at least one non-space character for name
    if not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", time) or not name.strip():
        await update.message.reply_text(
            "Invalid format. Usage: /add <reminder time> <reminder name>\nExample: /add 20:00 Medicine"
        )
        return
    user_id = (
        update.effective_user.id
        if update.effective_user and hasattr(update.effective_user, "id")
        else None
    )
    if user_id is None:
        await update.message.reply_text("Could not determine user id.")
        return
    add_reminder_to_db(user_id, time, name)
    await update.message.reply_text(f'Ok, I\'ll remind you at {time} for "{name}".')


if __name__ == "__main__":
    # Entry point for running the bot
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN not set in environment.")
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    # Register command handlers
    start_handler = CommandHandler("start", start)
    add_handler = CommandHandler("add", add)
    list_handler = CommandHandler("list", list_reminders)
    delete_handler = CommandHandler("delete", delete_reminder)
    application.add_handler(start_handler)
    application.add_handler(add_handler)
    application.add_handler(list_handler)
    application.add_handler(delete_handler)
    application.run_polling()  # Start polling for updates
