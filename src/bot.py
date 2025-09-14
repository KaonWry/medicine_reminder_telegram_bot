import logging  # For logging bot activity
import os  # For file path and environment variable access
import sqlite3  # For SQLite database operations
from dotenv import load_dotenv  # For loading environment variables from .env
from apscheduler.schedulers.background import BackgroundScheduler  # For scheduled jobs
from telegram import Update  # Telegram update object

# Bot framework
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
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
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE reminders SET triggered_today = 0")
    conn.commit()
    conn.close()


# Command Handlers
# /start
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


if __name__ == "__main__":
    # Check for BOT_TOKEN
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN not set in environment.")
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register command handlers
    start_handler = CommandHandler("start", start)
    list_handler = CommandHandler("list", list_reminders)

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
