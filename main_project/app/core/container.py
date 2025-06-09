"""
Dependency injection container for the application.
"""
import logging
from typing import Optional

from main_project.app.bot.telegram_bot import TelegramBot
from main_project.app.core.config import Config
from main_project.app.core.mongo_connection import MongoConnection
from main_project.app.schedulers.job_search_scheduler import JobSearchScheduler
from main_project.app.core.job_search_manager import JobSearchManager
from shared.data import StreamManager
from main_project.app.core.stores.job_search_store import JobSearchStore
from main_project.app.core.stores.sent_jobs_store import SentJobsStore

logger = logging.getLogger(__name__)

class Container:
    """Dependency injection container."""
    
    def __init__(self):
        """Initialize the container."""
        self._config: Optional[Config] = None
        self._mongo_connection: Optional[MongoConnection] = None
        self._job_search_store: Optional[JobSearchStore] = None
        self._sent_jobs_store: Optional[SentJobsStore] = None
        self._job_search_manager: Optional[JobSearchManager] = None
        self._telegram_bot: Optional['TelegramBot'] = None
        self._scheduler: Optional[JobSearchScheduler] = None
        self._stream_manager: Optional[StreamManager] = None
    
    @property
    def config(self) -> Config:
        """Get the configuration instance."""
        if not self._config:
            self._config = Config()
        return self._config
    
    @property
    def mongo_connection(self) -> MongoConnection:
        if not self._mongo_connection:
            self._mongo_connection = MongoConnection()
        return self._mongo_connection
    
    @property
    def job_search_store(self) -> JobSearchStore:
        if not self._job_search_store:
            self._job_search_store = JobSearchStore(self.mongo_connection)
        return self._job_search_store
    
    @property
    def sent_jobs_store(self) -> SentJobsStore:
        if not self._sent_jobs_store:
            self._sent_jobs_store = SentJobsStore(self.mongo_connection)
        return self._sent_jobs_store
    
    @property
    def job_search_manager(self) -> JobSearchManager:
        """Get the job search manager instance."""
        if not self._job_search_manager:
            self._job_search_manager = JobSearchManager(job_search_store=self.job_search_store, job_search_scheduler=self.scheduler)
        return self._job_search_manager
    
    @property
    def telegram_bot(self) -> 'TelegramBot':
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
    def stream_manager(self) -> StreamManager:
        if self._stream_manager is None:
            self._stream_manager = StreamManager()
        return self._stream_manager
    
    @property
    def scheduler(self) -> JobSearchScheduler:
        """Get the job search scheduler instance."""
        if not self._scheduler:
            self._scheduler = JobSearchScheduler(
                sent_jobs_store=self.sent_jobs_store,
                stream_manager=self.stream_manager
            )
        return self._scheduler
    

    
    async def initialize(self) -> None:
        """Initialize all services."""
        try:
            await self.mongo_connection.connect()
            await self.job_search_store.connect()
            await self.sent_jobs_store.connect()
            await self.telegram_bot.initialize()
            await self.scheduler.initialize()
            await self.job_search_manager.initialize()
            logger.info("All services initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown all services."""
        try:
            if self._scheduler and hasattr(self._scheduler, '_running'):
                await self._scheduler.stop()
            if self._telegram_bot and hasattr(self._telegram_bot, 'application'):
                await self._telegram_bot.stop()
            if self._mongo_connection and hasattr(self._mongo_connection, 'client'):
                await self._mongo_connection.close()
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