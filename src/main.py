"""
Main application entry point.
"""
import asyncio
import logging
import os
import signal
from pathlib import Path

from src.core.config import config
from src.core.linkedin_scraper import LinkedInScraper
from src.schedulers.job_search_scheduler import JobSearchScheduler
from src.utils.logging_config import setup_logging
from src.bot.telegram_bot import TelegramBot
from src.user.job_search import job_search_manager, set_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Application:
    def __init__(self):
        self.telegram_bot = None
        self.job_search_scheduler = None
        self.scraper = None
        self._running = False
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self._running = False
        
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, signal_handler)
    
    async def shutdown(self):
        """Shutdown the application gracefully."""
        logger.info("Shutting down application...")
        
        if self.job_search_scheduler:
            await self.job_search_scheduler.stop()
            logger.info("Job search scheduler stopped")
        
        if self.telegram_bot:
            await self.telegram_bot.stop()
            logger.info("Telegram bot stopped")
        
        if self.scraper:
            await self.scraper.close()
            logger.info("LinkedIn scraper closed")
    
    async def run(self):
        """Run the application."""
        try:
            # Set up signal handlers
            self._setup_signal_handlers()
            
            # Validate configuration
            if not config.validate():
                logger.error("Invalid configuration. Exiting...")
                return
            
            # Initialize LinkedIn scraper
            logger.info("Initializing LinkedIn scraper...")
            self.scraper = LinkedInScraper()
            await self.scraper.initialize()
            
            # Login to LinkedIn
            logger.info("Logging in to LinkedIn...")
            if not await self.scraper.login():
                logger.error("Failed to log in to LinkedIn. Exiting...")
                return
            logger.info("Successfully logged in to LinkedIn")
            
            # Initialize components
            self.telegram_bot = TelegramBot(config.telegram_bot_token)
            self.job_search_scheduler = JobSearchScheduler(self.scraper, self.telegram_bot)
            
            # Connect the scheduler to the job search manager
            set_scheduler(self.job_search_scheduler)
            
            # Initialize and start components
            await self.telegram_bot.initialize()
            await self.job_search_scheduler.start()
            logger.info("Job search scheduler started")
            
            # Start bot polling
            await self.telegram_bot.start_polling()
            
            # Mark as running
            self._running = True
            
            # Keep the application running until shutdown is requested
            while self._running:
                await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Application error: {e}", exc_info=True)
        finally:
            await self.shutdown()

def main():
    """Application entry point."""
    # Set up logging
    log_file = Path("logs/jobs_alerts.log")
    setup_logging(log_file)
    
    # Create and run the application
    app = Application()
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
    finally:
        logger.info("Application shutdown complete")

if __name__ == "__main__":
    main() 