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
        """Initialize the scheduler."""
        await self.start()
    
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
            filter_text=getattr(job_search, 'filter_text', None),
            callback_url=callback_url,
            job_search_id=job_search.id,
            user_id=job_search.user_id,
        )
        
        response = await search_jobs_via_scraper(params)
        log_data["callback_url"] = callback_url
        log_data["status_code"] = response.status_code
        if 200 <= response.status_code < 300:
            logger.info(f"Successfully triggered scraper job: {log_data}")
        else:
            log_data["response_text"] = response.text
            logger.error(f"Failed to trigger scraper job: {log_data}") 