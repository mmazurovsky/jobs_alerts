"""
Telegram bot implementation for Jobs Alerts.
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

from core.config import config
from core.linkedin_scraper import JobListing

logger = logging.getLogger(__name__)

# Store user IDs that have started the bot
active_users: Dict[int, bool] = {}

async def error_handler(update: Optional[Update], context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the bot."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    if update:
        await update.message.reply_text("Sorry, something went wrong. Please try again later.")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        f"Hi {user.mention_html()}!\n"
        "I'm your Jobs Alert bot. I'll notify you about new job postings that match your criteria.\n"
        "Use /help to see available commands."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "Available commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/search <keywords> [location] - Search for jobs\n"
        "/subscribe <keywords> [location] - Subscribe to job alerts\n"
        "/unsubscribe - Unsubscribe from job alerts\n"
        "/status - Show current subscription status"
    )

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search for jobs with the given keywords and location."""
    if not context.args:
        await update.message.reply_text(
            "Please provide search keywords.\n"
            "Usage: /search <keywords> [location]\n"
            "Example: /search 'python developer' 'San Francisco'"
        )
        return

    keywords = context.args[0]
    location = " ".join(context.args[1:]) if len(context.args) > 1 else ""
    
    await update.message.reply_text(f"Searching for '{keywords}' jobs in '{location}'...")
    
    # Search for jobs using the scraper
    async with LinkedInScraper() as scraper:
        if not await scraper.login():
            await update.message.reply_text("Failed to connect to LinkedIn. Please try again later.")
            return
            
        jobs = await scraper.search_jobs(keywords, location)
        if not jobs:
            await update.message.reply_text("No jobs found matching your criteria.")
            return
            
        # Send job listings
        for job in jobs[:5]:  # Limit to 5 jobs to avoid spam
            message = (
                f"🔍 *{job.title}*\n"
                f"🏢 {job.company}\n"
                f"📍 {job.location}\n"
                f"🔗 [View Job]({job.link})\n\n"
                f"{job.description[:200]}..."  # Truncate description
            )
            await update.message.reply_markdown_v2(message)
            
        if len(jobs) > 5:
            await update.message.reply_text(
                f"Found {len(jobs)} jobs in total. Showing first 5 results."
            )

async def setup_bot() -> Application:
    """Set up the Telegram bot with all handlers."""
    if not config.telegram_bot_token:
        logger.error("Telegram bot token not configured")
        return None
        
    application = Application.builder().token(config.telegram_bot_token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search_command))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    await application.initialize()
    await application.start()
    
    return application

async def send_job_notifications(job_title: str, company: str, location: str, job_url: str) -> None:
    """Send job notifications to subscribed users."""
    try:
        if not config.telegram_bot_token:
            logger.warning("Telegram bot token not configured, skipping notifications")
            return
            
        application = Application.builder().token(config.telegram_bot_token).build()
        
        message = (
            f"🔔 *New Job Alert*\n\n"
            f"🔍 *{job_title}*\n"
            f"🏢 {company}\n"
            f"📍 {location}\n"
            f"🔗 [View Job]({job_url})"
        )
        
        # TODO: Implement user subscription storage and send to all subscribed users
        # For now, just log the notification
        logger.info(f"Would send notification: {message}")
        
    except Exception as e:
        logger.error(f"Failed to send job notification: {e}")

async def send_broadcast_message(message: str) -> None:
    """Send a broadcast message to all active users."""
    try:
        if not config.telegram_bot_token:
            logger.warning("Telegram bot token not configured, skipping broadcast")
            return
            
        application = Application.builder().token(config.telegram_bot_token).build()
        await application.initialize()
        
        # TODO: Implement user subscription storage and send to all subscribed users
        # For now, just log the message
        logger.info(f"Would broadcast message: {message}")
        
        await application.stop()
        
    except Exception as e:
        logger.error(f"Failed to send broadcast message: {e}")

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