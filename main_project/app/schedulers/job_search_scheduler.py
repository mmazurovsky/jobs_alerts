"""
Job search scheduler for periodic job checks using APScheduler.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import os
import random
import re

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from shared.data import JobSearchOut, StreamManager, TimePeriod, JobListing, StreamType, StreamEvent, SearchJobsParams
from main_project.app.core.stores.sent_jobs_store import SentJobsStore
from main_project.app.core.mongo_connection import MongoConnection
from main_project.app.scraper_client import search_jobs_via_scraper

logger = logging.getLogger(__name__)

class JobSearchScheduler:
    """Scheduler for periodic job searches using APScheduler."""
    
    def __init__(self, stream_manager: StreamManager, sent_jobs_store: SentJobsStore):
        """Initialize the scheduler."""
        self._stream_manager = stream_manager
        self._scheduler = AsyncIOScheduler()
        self._active_searches: Dict[str, JobSearchOut] = {}  # search_id -> JobSearch
        self._sent_jobs_store = sent_jobs_store
        self._semaphore = asyncio.Semaphore(4)  # Limit to 4 concurrent jobs
        self._main_loop = None
    
    async def initialize(self) -> None:
        """Initialize the scheduler and add default jobs."""
        logger.info("Initializing job search scheduler...")
        try:
            await self.start()
            await self._add_default_jobs()
            logger.info("Job search scheduler initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}")
            raise

    async def _add_default_jobs(self) -> None:
        """Add default scheduled jobs."""
        # Every 5 minutes: Check for pending job searches
        self.scheduler.add_job(
            self._run_pending_job_searches_wrapper,
            'interval',
            minutes=5,
            id='check_pending_jobs',
            replace_existing=True,
            max_instances=1
        )

        # Every hour: Process expired subscriptions
        self.scheduler.add_job(
            self._process_expired_subscriptions_wrapper,
            'interval',
            hours=1,
            id='process_expired_subscriptions',
            replace_existing=True,
            max_instances=1
        )

        # Every 6 hours: Payment recovery
        self.scheduler.add_job(
            self._payment_recovery_wrapper,
            'interval',
            hours=6,
            id='payment_recovery',
            replace_existing=True,
            max_instances=1
        )

        logger.info("Default scheduled jobs added")

    async def _process_expired_subscriptions_wrapper(self) -> None:
        """Process expired subscriptions with proper error handling."""
        try:
            from main_project.app.core.container import get_container
            container = get_container()
            await container.premium_service.process_expired_subscriptions()
        except Exception as e:
            logger.error(f"Error processing expired subscriptions: {e}")

    async def _payment_recovery_wrapper(self) -> None:
        """Recover orphaned payments with proper error handling."""
        try:
            from main_project.app.core.container import get_container
            container = get_container()
            await container.payment_recovery_service.recover_orphaned_payments()
        except Exception as e:
            logger.error(f"Error in payment recovery: {e}")

    async def start(self) -> None:
        """Start the scheduler."""
        # Store the main event loop
        self._main_loop = asyncio.get_running_loop()
        # Start the APScheduler
        self._scheduler.start()
        logger.info("Job search scheduler started")
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        # Shutdown the APScheduler
        self._scheduler.shutdown()
        self._active_searches.clear()
        logger.info("Job search scheduler stopped")
    
    async def add_initial_job_searches(self, job_searches: List[JobSearchOut]) -> None:
        """Add initial job searches from manager."""
        try:
            for search in job_searches:
                await self.add_job_search(search)
        except Exception as e:
            logger.error(f"Error adding initial job searches: {e}")

    async def add_job_search(self, search: JobSearchOut) -> None:
        """Add a new job search from manager."""
        try:
            # Only add if not already present
            if search.id not in self._active_searches:
                self._active_searches[search.id] = search
                self._schedule_job_search(search)
            else:
                logger.info(f"Job search already exists: {search.id}")
        except Exception as e:
            logger.error(f"Error adding job search: {e}")

    async def remove_job_search(self, search_id: str) -> None:
        """Remove a job search from the scheduler."""
        try:
            if search_id in self._active_searches:
                # Remove from scheduler
                job_id = f"job_search_{search_id}"
                if self._scheduler.get_job(job_id):
                    self._scheduler.remove_job(job_id)
                
                # Remove from active searches
                del self._active_searches[search_id]
                
                logger.info(f"Removed job search: {search_id}")
            else:
                logger.warning(f"Job search not found: {search_id}")
        except Exception as e:
            logger.error(f"Error removing job search: {e}")

    def _schedule_job_search(self, search: JobSearchOut) -> None:
        """Schedule a job search to run periodically."""
        job_id = f"job_search_{search.id}"
        trigger = search.time_period.get_cron_trigger()

        async def job_wrapper():
            async with self._semaphore:
                await self.trigger_scraper_job_and_log(search)

        def schedule_job():
            # Use run_coroutine_threadsafe to schedule on the main event loop
            if self._main_loop is not None:
                asyncio.run_coroutine_threadsafe(job_wrapper(), self._main_loop)
            else:
                logger.error("Main event loop is not set. Cannot schedule job.")

        self._scheduler.add_job(
            schedule_job,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            coalesce=True,
        )
        logger.info(f"Scheduled job search {search.id} with trigger {trigger}")
    
    async def _check_job_searches(self) -> None:
        """Check all active job searches for new listings concurrently."""
        logger.info(f"Checking {len(self._active_searches)} job searches")
        
        # Create tasks for all job searches
        search_tasks = [
            self.trigger_scraper_job_and_log(job_search)
            for job_search in self._active_searches.values()
        ]
        
        # Run all searches concurrently
        try:
            await asyncio.gather(*search_tasks)
        except Exception as e:
            logger.error(f"Error during concurrent job searches: {e}")
            # Individual search errors are handled in trigger_scraper_job_and_log

    async def trigger_scraper_job_and_log(self, job_search: JobSearchOut):
        # Log all job search parameters
        log_data = {
            "job_search_id": job_search.id,
            "user_id": job_search.user_id,
            "keywords": job_search.job_title,
            "location": job_search.location,
            "job_types": [jt.label for jt in job_search.job_types] if job_search.job_types else [],
            "remote_types": [rt.label for rt in job_search.remote_types] if job_search.remote_types else [],
            "time_period": job_search.time_period.display_name if job_search.time_period else None,
        }
        logger.info(f"Requesting scraper job: {log_data}")
        # Build callback URL by appending the path to the base URL from env
        base_url = os.getenv("CALLBACK_URL")
        callback_url = base_url.rstrip("/") + "/job_results_callback"
        params = SearchJobsParams(
            keywords=job_search.job_title,
            location=job_search.location,
            job_types=log_data["job_types"],
            remote_types=log_data["remote_types"],
            time_period=log_data["time_period"],
        ).model_dump(exclude_none=True)
        params["callback_url"] = callback_url
        params["job_search_id"] = job_search.id
        params["user_id"] = job_search.user_id
        response = await search_jobs_via_scraper(params)
        log_data["callback_url"] = callback_url
        log_data["status_code"] = response.status_code
        if 200 <= response.status_code < 300:
            logger.info(f"Successfully triggered scraper job: {log_data}")
        else:
            log_data["response_text"] = response.text
            logger.error(f"Failed to trigger scraper job: {log_data}") 

    async def _run_pending_job_searches_wrapper(self) -> None:
        """Wrapper for running pending job searches with error handling."""
        try:
            from main_project.app.core.container import get_container
            container = get_container()
            
            # Get all active job searches from database
            all_searches = await container.job_search_store.get_all_searches()
            active_searches = [search for search in all_searches if getattr(search, 'is_active', True)]
            
            logger.info(f"Running {len(active_searches)} active job searches")
            
            # Process active searches with concurrency limit
            tasks = []
            for search in active_searches:
                # Check if it's time to run this search based on its time period
                if self._should_run_search(search):
                    task = asyncio.create_task(self._run_single_search_safe(search))
                    tasks.append(task)
                    
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except Exception as e:
            logger.error(f"Error in run pending job searches: {e}")

    async def _run_single_search_safe(self, search: JobSearchOut) -> None:
        """Run a single search with error handling and concurrency control."""
        async with self._semaphore:
            try:
                await self.trigger_scraper_job_and_log(search)
            except Exception as e:
                logger.error(f"Error running search {search.id}: {e}")

    def _should_run_search(self, search: JobSearchOut) -> bool:
        """Determine if a search should be run based on its time period."""
        # For now, run all searches every time the scheduled job runs
        # This could be optimized to track last run times
        return True 