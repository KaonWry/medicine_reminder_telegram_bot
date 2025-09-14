from telegram.ext import CommandHandler, MessageHandler, filters, ConversationHandler
from helpers import get_user_data, get_user_id, get_message_text, get_reminders_for_user
import sqlite3
import logging
from telegram.ext import ConversationHandler

DELETE_CHOOSE = 0


async def delete_reminder(update, context):
    """
    Delete a reminder from the database.
    Usage: /delete <number>
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
    conn = sqlite3.connect(get_reminders_for_user.__globals__["DB_PATH"])
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM reminders WHERE id = ? AND user_id = ?", (rem_id, user_id)
    )
    conn.commit()
    conn.close()
    await update.message.reply_text(f"Deleted reminder {idx}: {t} - {n}")
    logging.info(f"User {user_id} deleted reminder {idx}: '{n}' at {t}")


async def delete_start(update, context):
    """
    Start the delete reminder conversation.
    Lists reminders and prompts user to choose one to delete.
    Args:
        update: Telegram update object
        context: Telegram context object
    Returns:
        Next conversation state or END
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


async def delete_choose(update, context):
    """
    Prompts the user to choose a reminder to delete.
    Args:
        update: Telegram update object
        context: Telegram context object
    Returns:
        Next conversation state or END
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
    conn = sqlite3.connect(get_reminders_for_user.__globals__["DB_PATH"])
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


async def delete_cancel(update, context):
    """
    Cancels the delete reminder conversation.
    Args:
        update: Telegram update object
        context: Telegram context object
    Returns:
        None
    """
    if update.message:
        await update.message.reply_text("Reminder deletion cancelled.")
    return ConversationHandler.END


delete_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("delete", delete_start, filters=filters.Regex(r"^/delete$"))
    ],
    states={
        DELETE_CHOOSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_choose)],
    },
    fallbacks=[CommandHandler("cancel", delete_cancel)],
)
