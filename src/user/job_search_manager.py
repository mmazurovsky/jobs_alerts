"""
Job search manager for handling user job searches.
"""
import logging
from typing import Dict, List, Optional
import uuid
from src.data.data import JobSearchOut, JobSearchIn, JobSearchRemove, JobType, RemoteType, StreamManager, TimePeriod, StreamType, StreamEvent
from src.data.mongo_manager import MongoManager
import asyncio

from src.schedulers.job_search_scheduler import JobSearchScheduler

logger = logging.getLogger(__name__)

class JobSearchManager:
    """Manager for job searches."""
    
    def __init__(self, mongo_manager: MongoManager, job_search_scheduler: JobSearchScheduler):
        """Initialize job search manager."""
        self.job_searches: Dict[int, List[JobSearchOut]] = {}
        self._mongo_manager = mongo_manager
        self._job_search_scheduler = job_search_scheduler
        
    
    async def initialize(self) -> None:
        """Initialize job searches from MongoDB."""
        try:
            searches = await self._mongo_manager.get_all_searches()
            for search in searches:
                if search.user_id not in self.job_searches:
                    self.job_searches[search.user_id] = []
                self.job_searches[search.user_id].append(search)

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
                user_id=search_in.user_id
            )
            # Save to MongoDB first
            await self._mongo_manager.save_job_search(search)
            
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
    
    async def delete_search(self, job_search_remove: JobSearchRemove) -> bool:
        """Delete a job search."""
        try:
            # Delete from MongoDB first
            if not await self._mongo_manager.delete_search(job_search_remove.search_id):
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
        return self.job_searches.get(user_id, [])
    
    async def get_active_job_searches(self) -> List[JobSearchOut]:
        """Get all job searches."""
        active_searches = []
        for searches in self.job_searches.values():
            active_searches.extend(searches)
        return active_searches
    