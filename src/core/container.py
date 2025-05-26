"""
Dependency injection container for the application.
"""
import logging
from typing import Optional

from src.bot.telegram_bot import TelegramBot
from src.core.config import Config
from src.core.linkedin_scraper import LinkedInScraper
from src.data.mongo_manager import MongoManager
from src.schedulers.job_search_scheduler import JobSearchScheduler
from src.user.job_search_manager import JobSearchManager
from src.data.data import StreamManager

logger = logging.getLogger(__name__)

class Container:
    """Dependency injection container."""
    
    def __init__(self):
        """Initialize the container."""
        self._config: Optional[Config] = None
        self._mongo_manager: Optional[MongoManager] = None
        self._job_search_manager: Optional[JobSearchManager] = None
        self._scraper: Optional[LinkedInScraper] = None
        self._telegram_bot: Optional[TelegramBot] = None
        self._scheduler: Optional[JobSearchScheduler] = None
        self._stream_manager: Optional[StreamManager] = None
    
    @property
    def config(self) -> Config:
        """Get the configuration instance."""
        if not self._config:
            self._config = Config()
        return self._config
    
    @property
    def mongo_manager(self) -> MongoManager:
        """Get the MongoDB manager instance."""
        if not self._mongo_manager:
            self._mongo_manager = MongoManager()
        return self._mongo_manager
    
    @property
    def job_search_manager(self) -> JobSearchManager:
        """Get the job search manager instance."""
        if not self._job_search_manager:
            self._job_search_manager = JobSearchManager(mongo_manager=self.mongo_manager, job_search_scheduler=self.scheduler)
        return self._job_search_manager
    
    @property
    def scraper(self) -> LinkedInScraper:
        """Get the LinkedIn scraper instance."""
        if not self._scraper:
            self._scraper = LinkedInScraper(StreamManager())
        return self._scraper
    
    @property
    def telegram_bot(self) -> TelegramBot:
        """Get the Telegram bot instance."""
        if not self._telegram_bot:
            token = self.config.telegram_bot_token
            if not token:
                raise ValueError("TELEGRAM_BOT_TOKEN not set in configuration")
            self._telegram_bot = TelegramBot(
                token=token,
                stream_manager=self.stream_manager,
                job_search_manager=self.job_search_manager
            )
        return self._telegram_bot
    
    @property
    def scheduler(self) -> JobSearchScheduler:
        """Get the job search scheduler instance."""
        if not self._scheduler:
            self._scheduler = JobSearchScheduler(
                scraper=self.scraper,
                stream_manager=self.stream_manager
            )
        return self._scheduler
    
    @property
    def stream_manager(self) -> StreamManager:
        if self._stream_manager is None:
            self._stream_manager = StreamManager()
        return self._stream_manager
    
    async def initialize(self) -> None:
        """Initialize all services."""
        try:
            # Initialize MongoDB first
            await self.mongo_manager.connect()
            
            # Initialize job search manager
            await self.job_search_manager.initialize()
            
            # Initialize LinkedIn scraper
            await self.scraper.initialize()
            
            # Initialize Telegram bot
            await self.telegram_bot.initialize()
            
            # Initialize scheduler last
            await self.scheduler.initialize()
            
            logger.info("All services initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            # Don't call shutdown here as it might cause issues with uninitialized services
            raise
    
    async def shutdown(self) -> None:
        """Shutdown all services."""
        try:
            # Shutdown scheduler first if it was initialized
            if self._scheduler and hasattr(self._scheduler, '_running'):
                await self._scheduler.stop()
            
            # Shutdown Telegram bot if it was initialized
            if self._telegram_bot and hasattr(self._telegram_bot, 'application'):
                await self._telegram_bot.stop()
            
            # Shutdown LinkedIn scraper if it was initialized
            if self._scraper and hasattr(self._scraper, 'browser'):
                await self._scraper.close()
            
            # Close MongoDB connection last if it was initialized
            if self._mongo_manager and hasattr(self._mongo_manager, 'client'):
                await self._mongo_manager.close()
            
            logger.info("All services shut down successfully")
            
        except Exception as e:
            logger.error(f"Error shutting down services: {e}")
            raise

# Global container instance
container: Optional[Container] = None

def get_container() -> Container:
    """Get the global container instance. This function should only be used in main.py."""
    global container
    if container is None:
        container = Container()
    return container 