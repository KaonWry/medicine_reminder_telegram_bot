from telegram.ext import CommandHandler, MessageHandler, filters, ConversationHandler
from helpers import (
    is_valid_time_format,
    get_user_data,
    get_user_id,
    get_message_text,
    get_reminders_for_user,
)
import sqlite3
import logging
from telegram.ext import ConversationHandler

ADD_TIME, ADD_NAME = range(2)


async def add_reminder_to_db(update, context):
    """
    Add a reminder to the database.
    Usage: /add <reminder time> <reminder name>
    Args:
        update: Telegram update object
        context: Telegram context object
    Returns:
        None
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
    conn = sqlite3.connect(get_reminders_for_user.__globals__["DB_PATH"])
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


async def add_start(update, context):
    """
    Start the conversation to add a reminder.
    Asks the user for the reminder time.
    Args:
        update: Telegram update object
        context: Telegram context object
    Returns:
        Conversation state or END
    """
    if not update.message:
        return ConversationHandler.END
    await update.message.reply_text(
        "Please type the time you want to be reminded in (HH:MM, 24-hour format):"
    )
    return ADD_TIME


async def add_time(update, context):
    """
    Handles the user's input for the reminder time.
    Args:
        update: Telegram update object
        context: Telegram context object
    Returns:
        Next conversation state or END
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


async def add_name(update, context):
    """
    Handles the user's input for the reminder name.
    
    Args:
        update: Telegram update object
        context: Telegram context object
    Returns:
        Next conversation state or END
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


async def add_cancel(update, context):
    """
    Cancel the add reminder conversation.
    Args:
        update: Telegram update object
        context: Telegram context object
    Returns:
        None
    """
    if update.message:
        await update.message.reply_text("Reminder creation cancelled.")
    return ConversationHandler.END

# Conversation handler for adding reminders
add_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("add", add_start, filters=filters.Regex(r"^/add$"))],
    states={
        ADD_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_time)],
        ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
    },
    fallbacks=[CommandHandler("cancel", add_cancel)],
)
