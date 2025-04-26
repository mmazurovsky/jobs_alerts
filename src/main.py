"""
Main application entry point.
"""
import asyncio
import logging
import os
import signal
from pathlib import Path

from core.config import config
from core.linkedin_scraper import LinkedInScraper
from schedulers.job_search_scheduler import JobSearchScheduler
from utils.logging_config import setup_logging
from bot.telegram_bot import TelegramBot
from user.job_search import job_search_manager, set_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
telegram_bot = None
job_search_scheduler = None

async def run_application():
    """
    Run the application.
    """
    global telegram_bot, job_search_scheduler
    
    # Validate configuration
    if not config.validate():
        logger.error("Invalid configuration. Exiting...")
        return
    
    # Initialize the Telegram bot
    telegram_bot = TelegramBot(config.telegram_token)
    
    # Verify login first
    async with LinkedInScraper() as scraper:
        login_successful = await scraper.login()
        if not login_successful:
            logger.error("Login verification failed. Exiting...")
            return
        else:
            logger.info("Successfully logged in to LinkedIn")
            
            # Initialize the job search scheduler
            job_search_scheduler = JobSearchScheduler(scraper, telegram_bot)
            
            # Connect the scheduler to the job search manager
            set_scheduler(job_search_scheduler)
            
            # Start the job search scheduler
            await job_search_scheduler.start()
            logger.info("Job search scheduler started")
    
    # Start the Telegram bot
    await telegram_bot.start()
    logger.info("Telegram bot started")

async def shutdown():
    """Shutdown the application gracefully."""
    global telegram_bot, job_search_scheduler
    
    logger.info("Shutting down application...")
    
    if job_search_scheduler:
        await job_search_scheduler.stop()
        logger.info("Job search scheduler stopped")
    
    if telegram_bot:
        await telegram_bot.stop()
        logger.info("Telegram bot stopped")

def main():
    """
    Application entry point.
    """
    # Set up logging
    log_file = Path("logs/jobs_alerts.log")
    setup_logging(log_file)
    
    # Set up signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))
    
    try:
        # Debug logging for environment variables
        logger.info("Checking environment variables at startup:")
        logger.info(f"LINKEDIN_EMAIL from env: {os.getenv('LINKEDIN_EMAIL', '')}")
        logger.info(f"LINKEDIN_EMAIL from config: {config.linkedin_email}")
        
        asyncio.run(run_application())
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)

if __name__ == "__main__":
    main() 