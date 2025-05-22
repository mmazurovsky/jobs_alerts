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
        self._already_sent_jobs: Dict[str, Set[str]] = {}  # search_id -> set of job_ids
        self._running = False
        self._background_task = None
    
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
        
        # Start the background task
        self._background_task = asyncio.create_task(self._run())
        
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
        self._already_sent_jobs.clear()
        
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
        logger.info("Starting scheduler background task")
        while self._running:
            try:
                logger.info(f"Checking {len(self._active_searches)} job searches")
                await self._check_job_searches()
                await asyncio.sleep(300)  # Check every 5 minutes
            except asyncio.CancelledError:
                logger.info("Scheduler background task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Wait a bit before retrying
    
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
                self._already_sent_jobs[search.id] = set()
                self._schedule_job_search(search)
                logger.info(f"Added new job search: {search.id}")
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
                
                # Remove from active searches and sent jobs
                del self._active_searches[search_id]
                if search_id in self._already_sent_jobs:
                    del self._already_sent_jobs[search_id]
                
                logger.info(f"Removed job search: {search_id}")
            else:
                logger.warning(f"Job search not found: {search_id}")
        except Exception as e:
            logger.error(f"Error removing job search: {e}")

    def _schedule_job_search(self, search: JobSearchOut) -> None:
        """Schedule a job search to run periodically."""
        job_id = f"job_search_{search.id}"
        trigger = search.time_period.get_cron_trigger()
        
        self._scheduler.add_job(
            self._search_jobs_and_send_write_message_event,
            trigger=trigger,
            args=[search],
            id=job_id,
            replace_existing=True
        )
        logger.info(f"Scheduled job search {search.id} with trigger {trigger}")
    
    async def _search_jobs_and_send_write_message_event(self, job_search: JobSearchOut):
        """Check a single job search for new listings."""
        try:
            # Create a new browser session for this job search
            scraper = LinkedInScraper()
            await scraper.create_new_session()
            
            # Initialize sent_jobs set if it doesn't exist
            if job_search.id not in self._already_sent_jobs:
                self._already_sent_jobs[job_search.id] = set()
            
            # Search for jobs
            jobs = await scraper.search_jobs(
                keywords=job_search.job_title,
                location=job_search.location,
                job_types=job_search.job_types,
                remote_types=job_search.remote_types,
                time_period=job_search.time_period
            )
            
            if jobs:
                # Filter out jobs that have already been sent
                new_jobs = [
                    job for job in jobs 
                    if job.link not in self._already_sent_jobs[job_search.id]
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
                        self._already_sent_jobs[job_search.id].add(job.link)
                    
                    # Create message data instance
                    message_data = {
                        "user_id": job_search.user_id,
                        "message": message
                    }
                    
                    # Send message through stream manager
                    self._stream_manager.publish(StreamEvent(
                        type=StreamType.SEND_MESSAGE,
                        data=message_data,
                        source="job_search_scheduler"
                    ))
                else:
                    # Create message data instance
                    message_data = {
                        "user_id": job_search.user_id,
                        "message": "No new jobs found matching your criteria."
                    }
                    
                    # Send message through stream manager
                    self._stream_manager.publish(StreamEvent(
                        type=StreamType.SEND_MESSAGE,
                        data=message_data,
                        source="job_search_scheduler"
                    ))
            
            # Close the browser session
            await scraper.close()
            
        except Exception as e:
            logger.error(f"Error checking job search: {e}")
            # Create error message data instance
            message_data = {
                "user_id": job_search.user_id,
                "message": "Sorry, there was an error checking for new jobs. Please try again later."
            }
            
            # Send error message through stream manager
            self._stream_manager.publish(StreamEvent(
                type=StreamType.SEND_MESSAGE,
                data=message_data,
                source="job_search_scheduler"
            ))
    
    async def _check_job_searches(self) -> None:
        """Check all active job searches for new listings concurrently."""
        logger.info(f"Checking {len(self._active_searches)} job searches")
        
        # Create tasks for all job searches
        search_tasks = [
            self._search_jobs_and_send_write_message_event(job_search)
            for job_search in self._active_searches.values()
        ]
        
        # Run all searches concurrently
        try:
            await asyncio.gather(*search_tasks)
        except Exception as e:
            logger.error(f"Error during concurrent job searches: {e}")
            # Individual search errors are handled in _search_jobs_and_send_write_message_event 