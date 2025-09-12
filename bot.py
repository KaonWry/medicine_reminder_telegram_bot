import logging
import os
import sqlite3
import re
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

DB_PATH = os.path.join(os.path.dirname(__file__), "reminders.db")


def add_reminder_to_db(user_id: int, time: str, name: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reminders (user_id, time, name) VALUES (?, ?, ?)",
        (user_id, time, name)
    )
    conn.commit()
    conn.close()

def get_reminders_for_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT time, name FROM reminders WHERE user_id = ? ORDER BY time", (user_id,)
    )
    reminders = cursor.fetchall()
    conn.close()
    return reminders
async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user and hasattr(update.effective_user, "id") else None
    if user_id is None or not update.message:
        if update.message:
            await update.message.reply_text("Could not determine user id.")
        return
    reminders = get_reminders_for_user(user_id)
    if not reminders:
        await update.message.reply_text("You have no reminders set.")
        return
    msg = "Your reminders:\n" + "\n".join([f"{t} - {n}" for t, n in reminders])
    await update.message.reply_text(msg)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    args = context.args if context.args else []
    if len(args) < 2 or not update.message:
        if update.message:
            await update.message.reply_text("Usage: /add <reminder time> <reminder name>")
        return
    time = args[0]
    name = " ".join(args[1:])
    # Regex: HH:MM (24-hour) and at least one non-space character for name
    if not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", time) or not name.strip():
        await update.message.reply_text(
            "Invalid format. Usage: /add <reminder time> <reminder name>\nExample: /add 20:00 Medicine"
        )
        return
    user_id = update.effective_user.id if update.effective_user and hasattr(update.effective_user, "id") else None
    if user_id is None:
        await update.message.reply_text("Could not determine user id.")
        return
    add_reminder_to_db(user_id, time, name)
    await update.message.reply_text(
        f'Ok, I\'ll remind you at {time} for "{name}".'
    )

if __name__ == "__main__":
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN not set in environment.")
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    start_handler = CommandHandler("start", start)
    add_handler = CommandHandler("add", add)
    list_handler = CommandHandler("list", list_reminders)
    application.add_handler(start_handler)
    application.add_handler(add_handler)
    application.add_handler(list_handler)
    application.run_polling()
