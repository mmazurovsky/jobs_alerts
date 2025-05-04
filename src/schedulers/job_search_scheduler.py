"""
Job search scheduler for periodic job checks using APScheduler.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.data.data import JobSearchOut, StreamManager, TimePeriod, JobListing, SentJobsTracker, StreamType, StreamEvent
from src.core.linkedin_scraper import LinkedInScraper

logger = logging.getLogger(__name__)

class JobSearchScheduler:
    """Scheduler for periodic job searches using APScheduler."""
    
    def __init__(self, scraper: LinkedInScraper, stream_manager: StreamManager):
        """Initialize the scheduler."""
        self._scraper = scraper
        self._stream_manager = stream_manager
        self._scheduler = AsyncIOScheduler()
        self._active_searches: Dict[str, JobSearchOut] = {}  # search_id -> JobSearch
        self._sent_jobs: Dict[str, Set[str]] = {}  # search_id -> set of job_ids
        self._running = True
        self._background_task = asyncio.create_task(self._run())
        
        # Subscribe to job search events
        self._stream_manager.get_stream(StreamType.JOB_SEARCH_PROCESSED).subscribe(
            lambda event: asyncio.create_task(self._handle_job_search_processed(event))
        )
        self._stream_manager.get_stream(StreamType.INITIAL_JOB_SEARCHES).subscribe(
            lambda event: asyncio.create_task(self._handle_initial_job_searches(event))
        )
    
    async def initialize(self) -> None:
        """Initialize the scheduler."""
        await self.start()
    
    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler is already running")
            return
        
        # Start the APScheduler
        self._scheduler.start()
        self._running = True
        
        logger.info("Job search scheduler started")
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            logger.warning("Scheduler is not running")
            return
        
        # Shutdown the APScheduler
        self._scheduler.shutdown()
        self._running = False
        self._active_searches.clear()
        self._sent_jobs.clear()
        
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None
        
        logger.info("Job search scheduler stopped")
    
    async def _run(self) -> None:
        """Run the scheduler loop."""
        while self._running:
            try:
                await self._check_job_searches()
                await asyncio.sleep(300)  # Check every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Wait a bit before retrying
    
    async def _handle_initial_job_searches(self, event: StreamEvent) -> None:
        """Handle initial job searches from manager."""
        try:
            job_searches = event.data["job_searches"]
            for search_data in job_searches:
                search = JobSearchOut(**search_data)
                if search.search_id not in self._active_searches:
                    self._active_searches[search.search_id] = search
                    self._sent_jobs[search.search_id] = set()
                    self._schedule_job_search(search)
                    logger.info(f"Added initial job search: {search.search_id}")
        except Exception as e:
            logger.error(f"Error handling initial job searches: {e}")
    
    async def _handle_job_search_processed(self, event: StreamEvent) -> None:
        """Handle processed job search from manager."""
        try:
            search_data = event.data["job_search"]
            search = JobSearchOut(**search_data)
            
            # Only add if not already present
            if search.search_id not in self._active_searches:
                self._active_searches[search.search_id] = search
                self._sent_jobs[search.search_id] = set()
                self._schedule_job_search(search)
                logger.info(f"Added new job search: {search.search_id}")
            else:
                logger.info(f"Job search already exists: {search.search_id}")
        except Exception as e:
            logger.error(f"Error handling job search: {e}")
    
    async def _check_job_search(self, job_search: JobSearchOut):
        """Check a single job search for new listings."""
        try:
            # Check if we need to search for this job yet
            last_check = self._last_check.get(job_search.id)
            if last_check and datetime.now() - last_check < timedelta(minutes=30):
                return
            
            # Search for jobs
            jobs = await self._scraper.search_jobs(
                title=job_search.title,
                location=job_search.location,
                experience=job_search.experience
            )
            
            if jobs:
                # Filter out jobs that have already been sent
                new_jobs = [
                    job for job in jobs 
                    if not self._sent_jobs_tracker.is_job_sent(job_search.user_id, job.link)
                ]
                
                if new_jobs:
                    # Format and send job listings
                    message = "🔔 New job listings found!\n\n"
                    for job in new_jobs:
                        message += (
                            f"🏢 {job.company}\n"
                            f"💼 {job.title}\n"
                            f"📍 {job.location}\n"
                            f"💼 {job.job_type}\n"
                            f"🔗 {job.link}\n\n"
                        )
                    
                    # Mark jobs as sent
                    for job in new_jobs:
                        self._sent_jobs_tracker.mark_job_sent(job_search.user_id, job.link)
                    
                    self.stream_manager.publish(StreamEvent(
                        type=StreamType.SEND_MESSAGE,
                        data={
                            "user_id": job_search.user_id,
                            "message": message
                        },
                        source="job_search_scheduler"
                    ))
                else:
                    self.stream_manager.publish(StreamEvent(
                        type=StreamType.SEND_MESSAGE,
                        data={
                            "user_id": job_search.user_id,
                            "message": "No new jobs found matching your criteria."
                        },
                        source="job_search_scheduler"
                    ))
            
            # Update last check time
            self._last_check[job_search.id] = datetime.now()
            
        except Exception as e:
            logger.error(f"Error checking job search: {e}")
            self.stream_manager.publish(StreamEvent(
                type=StreamType.SEND_MESSAGE,
                data={
                    "user_id": job_search.user_id,
                    "message": "Sorry, there was an error checking for new jobs. Please try again later."
                },
                source="job_search_scheduler"
            ))
    
    async def _check_job_searches(self) -> None:
        """Check all active job searches for new listings."""
        for job_search in self._active_searches.values():
            try:
                await self._check_job_search(job_search)
            except Exception as e:
                logger.error(f"Error checking job search {job_search.id}: {e}") 