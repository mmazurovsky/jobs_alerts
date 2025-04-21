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
from schedulers.job_scheduler import start_scheduler, stop_scheduler
from utils.logging_config import setup_logging
from bot.telegram_bot import setup_bot, send_job_notifications

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_application():
    """
    Run the application.
    """
    # Validate configuration
    if not config.validate():
        logger.error("Invalid configuration. Exiting...")
        return
    
    # Start the Telegram bot in the background
    bot_task = asyncio.create_task(setup_bot())

    # Verify login first
    async with LinkedInScraper() as scraper:
        login_successful = await scraper.login()
        if not login_successful:
            logger.error("Login verification failed. Exiting...")
            return
        else:
            logger.info("Successfully logged in to LinkedIn")
            # Example search parameters - you can make these configurable
            keywords = "solution architect"
            location = "Germany"
            
            jobs = await scraper.search_jobs(keywords, location)
            logger.info(f"Found {len(jobs)} jobs")
            
            if jobs:
                # Send notifications for each job
                for job in jobs:
                    await send_job_notifications(
                        job_title=job.title,
                        company=job.company,
                        location=job.location,
                        job_url=job.job_url
                    )
    

    
    # Keep the application running without starting the scheduler yet
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        stop_scheduler()
        bot_task.cancel()

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
        loop.add_signal_handler(sig, lambda: asyncio.create_task(stop_scheduler()))
    
    try:
        # Debug logging for environment variables
        logger.info("Checking environment variables at startup:")
        logger.info(f"AGENTQL_API_KEY from env: {os.getenv('AGENTQL_API_KEY', '')[:5]}...")
        logger.info(f"AGENTQL_API_KEY from config: {config.agentql_api_key[:5]}...")
        logger.info(f"LINKEDIN_EMAIL from env: {os.getenv('LINKEDIN_EMAIL', '')}")
        logger.info(f"LINKEDIN_EMAIL from config: {config.linkedin_email}")
        
        asyncio.run(run_application())
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)

if __name__ == "__main__":
    main() 