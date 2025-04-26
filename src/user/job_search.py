"""
Job search management for users.
"""
from typing import Dict, List, Optional
from datetime import datetime
import uuid
from src.data.data import JobSearchOut, JobSearchIn, JobType, RemoteType, TimePeriod

# Global scheduler instance
_scheduler = None

class JobSearchManager:
    """Manages job searches for users."""
    
    def __init__(self):
        """Initialize the job search manager."""
        # Map of user_id to list of JobSearchData
        self._job_searches: Dict[int, List[JobSearchOut]] = {}
    
    def add_job_search(self, new_search: JobSearchIn) -> JobSearchOut:
        """Add a new job search for a user."""
        if new_search.user_id not in self._job_searches:
            self._job_searches[new_search.user_id] = []
        
        job_search = JobSearchOut(
            id=str(uuid.uuid4()),
            job_title=new_search.job_title,
            location=new_search.location,
            job_types=new_search.job_types,
            remote_types=new_search.remote_types,
            time_period=new_search.time_period,
            user_id=new_search.user_id,
            created_at=datetime.now()
        )
        self._job_searches[new_search.user_id].append(job_search)
        
        # Notify the scheduler about the new job search
        self._notify_scheduler()
        
        return job_search
    
    def remove_job_search(self, user_id: int, search_id: str) -> bool:
        """Remove a job search for a user by search ID."""
        if user_id not in self._job_searches:
            return False
        
        # Find and remove the job search with matching ID
        for i, search in enumerate(self._job_searches[user_id]):
            if search.id == search_id:
                self._job_searches[user_id].pop(i)
                # Notify the scheduler about the removed job search
                self._notify_scheduler()
                return True
        return False
    
    def get_user_job_searches(self, user_id: int) -> List[JobSearchOut]:
        """Get all job searches for a user."""
        return self._job_searches.get(user_id, [])
    
    def get_active_job_searches(self) -> List[JobSearchOut]:
        """Get all active job searches across all users."""
        all_searches = []
        for searches in self._job_searches.values():
            all_searches.extend(searches)
        return all_searches
    
    def clear_user_job_searches(self, user_id: int) -> None:
        """Remove all job searches for a user."""
        if user_id in self._job_searches:
            del self._job_searches[user_id]
            # Notify the scheduler about the cleared job searches
            self._notify_scheduler()
    
    def _notify_scheduler(self) -> None:
        """Notify the scheduler about changes to job searches."""
        global _scheduler
        if _scheduler:
            # Update the scheduler with the latest job searches
            _scheduler.update_job_searches()

def set_scheduler(scheduler) -> None:
    """Set the global scheduler instance."""
    global _scheduler
    _scheduler = scheduler

# Create a singleton instance
job_search_manager = JobSearchManager()

# Helper functions for backward compatibility
def add_job_search(new_search: JobSearchIn) -> JobSearchOut:
    """Add a new job search for a user."""
    return job_search_manager.add_job_search(new_search)

def remove_job_search(user_id: int, search_id: str) -> bool:
    """Remove a job search for a user by search ID."""
    return job_search_manager.remove_job_search(user_id, search_id)

def get_user_job_searches(user_id: int) -> List[JobSearchOut]:
    """Get all job searches for a user."""
    return job_search_manager.get_user_job_searches(user_id)

def get_active_job_searches() -> List[JobSearchOut]:
    """Get all active job searches across all users."""
    return job_search_manager.get_active_job_searches() 