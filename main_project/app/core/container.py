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
from main_project.app.core.stores.user_subscription_store import UserSubscriptionStore
from main_project.app.core.stores.payment_transaction_store import PaymentTransactionStore
from main_project.app.services.premium_service import PremiumService
from main_project.app.services.payment_handler_service import PaymentHandlerService, PaymentRecoveryService

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
        self._user_subscription_store: Optional[UserSubscriptionStore] = None
        self._payment_transaction_store: Optional[PaymentTransactionStore] = None
        self._premium_service: Optional[PremiumService] = None
        self._payment_handler_service: Optional[PaymentHandlerService] = None
        self._payment_recovery_service: Optional[PaymentRecoveryService] = None
    
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
            self._job_search_manager = JobSearchManager(
                job_search_store=self.job_search_store,
                sent_jobs_store=self.sent_jobs_store
            )
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
                job_search_manager=self.job_search_manager,
                premium_service=self.premium_service,
                payment_handler_service=self.payment_handler_service
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
    
    @property
    def user_subscription_store(self) -> UserSubscriptionStore:
        if not self._user_subscription_store:
            self._user_subscription_store = UserSubscriptionStore(self.mongo_connection)
        return self._user_subscription_store
    
    @property
    def payment_transaction_store(self) -> PaymentTransactionStore:
        if not self._payment_transaction_store:
            self._payment_transaction_store = PaymentTransactionStore(self.mongo_connection)
        return self._payment_transaction_store
    
    @property
    def premium_service(self) -> PremiumService:
        if not self._premium_service:
            self._premium_service = PremiumService(
                user_subscription_store=self.user_subscription_store,
                job_search_store=self.job_search_store
            )
        return self._premium_service
    
    @property
    def payment_handler_service(self) -> PaymentHandlerService:
        if not self._payment_handler_service:
            self._payment_handler_service = PaymentHandlerService(
                payment_store=self.payment_transaction_store,
                subscription_store=self.user_subscription_store,
                premium_service=self.premium_service
            )
        return self._payment_handler_service
    
    @property
    def payment_recovery_service(self) -> PaymentRecoveryService:
        if not self._payment_recovery_service:
            self._payment_recovery_service = PaymentRecoveryService(
                payment_store=self.payment_transaction_store,
                payment_handler_service=self.payment_handler_service
            )
        return self._payment_recovery_service
    
    async def initialize(self) -> None:
        """Initialize all services."""
        try:
            await self.connect_all()
            await self.telegram_bot.initialize()
            await self.scheduler.initialize()
            await self.job_search_manager.initialize()
            logger.info("All services initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            raise
    
    async def connect_all(self) -> None:
        """Connect all stores to their respective databases."""
        await self.mongo_connection.connect()
        await self.job_search_store.connect()
        await self.sent_jobs_store.connect()
        await self.user_subscription_store.connect()
        await self.payment_transaction_store.connect()
    
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