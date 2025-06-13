"""
Job search manager for handling user job searches.
"""
import logging
from typing import Dict, List, Optional
import uuid
from shared.data import JobSearchOut, JobSearchIn, JobSearchRemove, JobType, RemoteType, StreamManager, TimePeriod, StreamType, StreamEvent, SearchJobsParams
from main_project.app.core.stores.job_search_store import JobSearchStore
import asyncio

from main_project.app.schedulers.job_search_scheduler import JobSearchScheduler
from main_project.app.scraper_client import search_jobs_via_scraper

logger = logging.getLogger(__name__)

class JobSearchManager:
    """Manager for job searches."""
    
    def __init__(self, job_search_store: JobSearchStore, job_search_scheduler: JobSearchScheduler):
        """Initialize job search manager."""
        self.job_searches: Dict[int, List[JobSearchOut]] = {}
        self._job_search_store = job_search_store
        self._job_search_scheduler = job_search_scheduler
        
    
    async def initialize(self) -> None:
        """Initialize job searches from MongoDB."""
        try:
            searches = await self._job_search_store.get_all_searches()
            for search in searches:
                if search.user_id not in self.job_searches:
                    self.job_searches[search.user_id] = []
                self.job_searches[search.user_id].append(search)
                logger.info(f"Loaded job search from MongoDB: {search.to_log_string()}")

            # Send initial job searches to scheduler directly
            await self._job_search_scheduler.add_initial_job_searches(searches)
            
            logger.info(f"Loaded {len(searches)} job searches from MongoDB")
        except Exception as e:
            logger.error(f"Error loading job searches from MongoDB: {e}")
    
    async def add_search(self, search_in: JobSearchIn) -> str:
        """Add a new job search.
        
        Returns:
            str: The ID of the created job search
        """
        try:
            search = JobSearchOut(
                id=str(uuid.uuid4()),
                job_title=search_in.job_title,
                location=search_in.location,
                job_types=search_in.job_types,
                remote_types=search_in.remote_types,
                time_period=search_in.time_period,
                user_id=search_in.user_id,
                blacklist=search_in.blacklist,
                filter_text=search_in.filter_text,
            )
            logger.info(f"Added new job search from user: {search.to_log_string()}")
            # Save to MongoDB first
            await self._job_search_store.save_job_search(search)
            
            # Update in-memory cache
            if search.user_id not in self.job_searches:
                self.job_searches[search.user_id] = []
            self.job_searches[search.user_id].append(search)
            
            # Add to scheduler directly
            await self._job_search_scheduler.add_job_search(search)
            
            return search.id
        except Exception as e:
            logger.error(f"Error adding job search: {e}")
            raise
    
    async def execute_one_time_search(self, search_in: JobSearchIn, user_id: int) -> None:
        """Execute a one-time search without saving it permanently.
        
        Args:
            search_in: Job search parameters
            user_id: Telegram user ID for sending results
        """
        try:
            logger.info(f"Executing one-time search for user {user_id}: {search_in.job_title} in {search_in.location}")
            
            # Create SearchJobsParams object
            params = SearchJobsParams(
                keywords=search_in.job_title,
                location=search_in.location,
                job_types=[jt.label for jt in search_in.job_types],
                remote_types=[rt.label for rt in search_in.remote_types],
                time_period="24 hours",  # Use 24 hours for one-time search
                max_jobs=100,  # Higher limit for one-time search
                blacklist=search_in.blacklist,
                user_id=user_id,
                filter_text=search_in.filter_text
            )
            
            # Execute search via scraper
            response = await search_jobs_via_scraper(params)
            
            if response.status_code == 200:
                logger.info(f"One-time search initiated successfully for user {user_id}")
            else:
                logger.error(f"One-time search failed for user {user_id}: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Error executing one-time search for user {user_id}: {e}")
            raise
    
    async def delete_search(self, job_search_remove: JobSearchRemove) -> bool:
        """Delete a job search."""
        try:
            # Delete from MongoDB first
            if not await self._job_search_store.delete_search(job_search_remove.search_id):
                return False
            
            # Delete from in-memory cache
            if job_search_remove.user_id in self.job_searches:
                self.job_searches[job_search_remove.user_id] = [
                    s for s in self.job_searches[job_search_remove.user_id] if s.id != job_search_remove.search_id
                ]
            
            # Remove from scheduler directly
            await self._job_search_scheduler.remove_job_search(job_search_remove.search_id)
            
            return True
        except Exception as e:
            logger.error(f"Error deleting job search: {e}")
            return False
    
    async def get_user_searches(self, user_id: int) -> List[JobSearchOut]:
        """Get all job searches for a user."""
        searches = await self._job_search_store.get_user_searches(user_id)
        for search in searches:
            logger.info(f"Loaded job search from MongoDB: {search.to_log_string()}")
        return searches
    
    async def get_active_job_searches(self) -> List[JobSearchOut]:
        """Get all job searches."""
        active_searches = []
        for searches in self.job_searches.values():
            active_searches.extend(searches)
        return active_searches
    