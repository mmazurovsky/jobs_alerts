"""
Telegram bot for jobs_alerts.
"""
import logging
import os
from typing import Dict, List, Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Import JobListing from the core module
from core.linkedin_scraper import JobListing

logger = logging.getLogger(__name__)

# Store user IDs that have started the bot
active_users: Dict[int, bool] = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    user = update.effective_user
    user_id = user.id

    logger.info(f"User {user_id} ({user.first_name}) started the bot")
    
    # Add user to active users
    active_users[user_id] = True
    
    welcome_message = (
        f"👋 Hello {user.first_name}!\n\n"
        f"Welcome to Jobs Alerts Bot. I'll notify you when new job opportunities "
        f"matching your criteria are found on LinkedIn.\n\n"
        f"Use /help to see available commands."
    )
    
    await update.message.reply_text(welcome_message)
    logger.info(f"User {user_id} ({user.first_name}) started the bot")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "Available commands:\n\n"
        "/start - Start the bot and receive job alerts\n"
        "/help - Show this help message\n"
        "/stop - Stop receiving job alerts"
    )
    
    await update.message.reply_text(help_text)

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stop sending job alerts to the user."""
    user_id = update.effective_user.id
    
    if user_id in active_users:
        del active_users[user_id]
        await update.message.reply_text(
            "You will no longer receive job alerts. Use /start to resume."
        )
        logger.info(f"User {user_id} stopped the bot")
    else:
        await update.message.reply_text(
            "You're not currently receiving alerts. Use /start to begin."
        )

async def send_job_notification(user_id: int, job: JobListing) -> None:
    """Send a job notification to a specific user.
    
    Args:
        user_id: The Telegram user ID to send the notification to
        job: The JobListing instance containing job details
    """
    if user_id not in active_users:
        logger.info(f"Skipping notification for inactive user {user_id}")
        return
    
    try:
        bot = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build().bot
        
        message = (
            f"🔔 New Job Alert!\n\n"
            f"📋 {job.title}\n"
            f"🏢 {job.company}\n"
            f"📍 {job.location}\n\n"
            f"🔗 {job.job_url}"
        )
        
        await bot.send_message(chat_id=user_id, text=message)
        logger.info(f"Sent job notification to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send notification to user {user_id}: {e}")

async def send_job_notifications(job: JobListing) -> None:
    """Send job notifications to all active users.
    
    Args:
        job: The JobListing instance containing job details
    """
    for user_id in active_users:
        await send_job_notification(user_id, job)

async def send_broadcast_message(message: str) -> None:
    """Send a broadcast message to all active users.
    
    Args:
        message: The message to send to all active users
    """
    try:
        bot = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build().bot
        
        for user_id in active_users:
            await bot.send_message(chat_id=user_id, text=message)
            logger.info(f"Sent broadcast message to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send broadcast message: {e}")

async def setup_bot() -> Application:
    """Set up the Telegram bot with all handlers."""
    application = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stop", stop_command))

    # Add error handler
    application.add_error_handler(error_handler)

    # Start the bot
    await application.initialize()
    await application.start()
    await application.update_bot()
    
    return application 