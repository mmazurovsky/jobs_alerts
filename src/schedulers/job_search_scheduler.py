"""
Job search scheduler for periodic job checks using APScheduler.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore

from src.data.data import JobSearchOut, TimePeriod, JobListing
from src.user.job_search import get_active_job_searches
from src.core.linkedin_scraper import LinkedInScraper
from src.bot.telegram_bot import TelegramBot

logger = logging.getLogger(__name__)

class JobSearchScheduler:
    """Scheduler for periodic job searches using APScheduler."""
    
    def __init__(self, scraper: LinkedInScraper, telegram_bot: TelegramBot):
        """Initialize the scheduler with a LinkedIn scraper and Telegram bot."""
        self.scraper = scraper
        self.telegram_bot = telegram_bot
        self._scheduler = AsyncIOScheduler(
            jobstores={'default': MemoryJobStore()},
            timezone='UTC'
        )
        self._running = False
        self._job_ids: Set[str] = set()
    
    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler is already running")
            return
        
        # Start the APScheduler
        self._scheduler.start()
        self._running = True
        
        # Schedule all active job searches
        await self._schedule_all_job_searches()
        
        logger.info("Job search scheduler started")
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            logger.warning("Scheduler is not running")
            return
        
        # Shutdown the APScheduler
        self._scheduler.shutdown()
        self._running = False
        self._job_ids.clear()
        
        logger.info("Job search scheduler stopped")
    
    async def _schedule_all_job_searches(self) -> None:
        """Schedule all active job searches."""
        active_searches = get_active_job_searches()
        
        # Remove jobs that are no longer active
        current_job_ids = {search.id for search in active_searches}
        for job_id in list(self._job_ids):
            if job_id not in current_job_ids:
                self._scheduler.remove_job(job_id)
                self._job_ids.remove(job_id)
                logger.info(f"Removed job search {job_id}")
        
        # Add or update jobs for active searches
        for search in active_searches:
            if search.id not in self._job_ids:
                # Create a new job for this search with the appropriate trigger
                trigger = search.time_period.get_cron_trigger()
                
                self._scheduler.add_job(
                    self._process_search,
                    trigger=trigger,
                    args=[search],
                    id=search.id,
                    name=f"Job search: {search.job_title}",
                    replace_existing=True
                )
                self._job_ids.add(search.id)
                logger.info(f"Scheduled job search {search.id}: {search.job_title} with time period {search.time_period.name}")
    
    async def _process_search(self, search: JobSearchOut) -> None:
        """Process a single job search."""
        logger.info(f"Processing search: {search.job_title}")
        try:
            jobs = await self.scraper.search_jobs(
                keywords=search.job_title,
                location=search.location,
                job_types=search.job_types,
                remote_types=search.remote_types
            )
            
            if jobs:
                # Send notifications for new jobs
                await self.telegram_bot.send_job_listings(search.user_id, jobs)
                logger.info(f"Sent {len(jobs)} job notifications to user {search.user_id}")
            else:
                logger.info(f"No new jobs found for {search.job_title}")
        except Exception as e:
            logger.error(f"Error processing job search {search.id}: {e}")
    
    async def update_job_searches(self) -> None:
        """Update scheduled job searches based on active searches."""
        if not self._running:
            logger.warning("Cannot update job searches: scheduler is not running")
            return
        
        await self._schedule_all_job_searches()
        logger.info("Updated scheduled job searches") 