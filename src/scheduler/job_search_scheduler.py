"""
Job search scheduler for periodic job checks.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from src.data.data import JobSearchConfig, TimePeriod
from src.user.job_search import get_active_job_searches, update_last_check
from src.core.linkedin_scraper import LinkedInScraper

logger = logging.getLogger(__name__)

class JobSearchScheduler:
    """Scheduler for periodic job searches."""
    
    def __init__(self, scraper: LinkedInScraper):
        """Initialize the scheduler with a LinkedIn scraper."""
        self.scraper = scraper
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler is already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Job search scheduler started")
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            logger.warning("Scheduler is not running")
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Job search scheduler stopped")
    
    async def _run(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                await self._check_job_searches()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _check_job_searches(self) -> None:
        """Check all active job searches."""
        active_searches = get_active_job_searches()
        for search in active_searches:
            if self._should_check_search(search):
                try:
                    await self._process_search(search)
                    update_last_check(search.user_id, search.job_title)
                except Exception as e:
                    logger.error(f"Error processing search {search.job_title}: {e}")
    
    def _should_check_search(self, search: JobSearchConfig) -> bool:
        """Check if a search should be processed based on its time period."""
        if not search.last_check:
            return True
        
        time_since_last_check = datetime.now() - search.last_check
        return time_since_last_check >= timedelta(seconds=search.time_period.seconds)
    
    async def _process_search(self, search: JobSearchConfig) -> None:
        """Process a single job search."""
        logger.info(f"Processing search: {search.job_title}")
        jobs = await self.scraper.search_jobs(
            keywords=search.job_title,
            location=search.location,
            job_types=search.job_types,
            remote_types=search.remote_types,
            max_jobs=search.max_jobs
        )
        
        # TODO: Send notifications for new jobs
        logger.info(f"Found {len(jobs)} jobs for {search.job_title}") 