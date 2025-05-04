"""
Job search manager for handling user job searches.
"""
import logging
from typing import Dict, List, Optional
import uuid
from src.data.data import JobSearchOut, JobSearchIn, JobType, RemoteType, StreamManager, TimePeriod, StreamType, StreamEvent
from src.data.mongo_manager import MongoManager
import asyncio

logger = logging.getLogger(__name__)

class JobSearchManager:
    """Manager for job searches."""
    
    def __init__(self, mongo_manager: MongoManager, stream_manager: StreamManager):
        """Initialize job search manager."""
        self.job_searches: Dict[int, List[JobSearchOut]] = {}
        self._mongo_manager = mongo_manager
        self._scheduler = None
        self.stream_manager = stream_manager
        
        # Subscribe to job search events
        self.stream_manager.get_stream(StreamType.JOB_SEARCH_ADD).subscribe(
            lambda event: asyncio.create_task(self._handle_job_search_add(event))
        )
        self.stream_manager.get_stream(StreamType.JOB_SEARCH_REMOVE).subscribe(
            lambda event: asyncio.create_task(self._handle_job_search_remove(event))
        )
    
    async def initialize(self) -> None:
        """Initialize job searches from MongoDB."""
        try:
            searches = await self._mongo_manager.get_all_searches()
            for search in searches:
                if search.user_id not in self.job_searches:
                    self.job_searches[search.user_id] = []
                self.job_searches[search.user_id].append(search)
            
            # Send initial job searches to scheduler
            self.stream_manager.publish(StreamEvent(
                type=StreamType.INITIAL_JOB_SEARCHES,
                data={
                    "job_searches": [search.model_dump() for search in searches]
                },
                source="job_search_manager"
            ))
            
            logger.info(f"Loaded {len(searches)} job searches from MongoDB")
        except Exception as e:
            logger.error(f"Error loading job searches from MongoDB: {e}")
    
    def set_scheduler(self, scheduler) -> None:
        """Set the scheduler for notifications."""
        self._scheduler = scheduler
    
    def _notify_scheduler(self) -> None:
        """Notify scheduler of job search changes."""
        if self._scheduler:
            self._scheduler.notify_job_search_changes()
    
    async def add_search(self, search: JobSearchOut) -> bool:
        """Add a new job search."""
        try:
            # Save to MongoDB first
            if not await self._mongo_manager.save_search(search):
                return False
            
            # Update in-memory cache
            if search.user_id not in self.job_searches:
                self.job_searches[search.user_id] = []
            self.job_searches[search.user_id].append(search)
            
            # Notify scheduler
            self._notify_scheduler()
            return True
        except Exception as e:
            logger.error(f"Error adding job search: {e}")
            return False
    
    async def delete_search(self, search_id: str, user_id: int) -> bool:
        """Delete a job search."""
        try:
            # Delete from MongoDB first
            if not await self._mongo_manager.delete_search(search_id):
                return False
            
            # Delete from in-memory cache
            if user_id in self.job_searches:
                self.job_searches[user_id] = [
                    s for s in self.job_searches[user_id] if s.id != search_id
                ]
            
            # Notify scheduler
            self._notify_scheduler()
            return True
        except Exception as e:
            logger.error(f"Error deleting job search: {e}")
            return False
    
    async def get_user_searches(self, user_id: int) -> List[JobSearchOut]:
        """Get all job searches for a user."""
        return self.job_searches.get(user_id, [])
    
    async def get_active_job_searches(self) -> List[JobSearchOut]:
        """Get all active job searches."""
        active_searches = []
        for searches in self.job_searches.values():
            active_searches.extend([s for s in searches if s.is_active])
        return active_searches
    
    async def clear_user_job_searches(self, user_id: int) -> None:
        """Clear all job searches for a user."""
        if user_id in self.job_searches:
            # Delete each search from MongoDB
            for search in self.job_searches[user_id]:
                await self._mongo_manager.delete_search(search.id)
            
            # Clear from in-memory cache
            del self.job_searches[user_id]
            
            # Notify scheduler
            self._notify_scheduler()
            
    async def _handle_job_search_add(self, event: StreamEvent):
        """Handle job search addition from Telegram Bot"""
        try:
            # Create JobSearchOut from JobSearchIn
            job_search_in = JobSearchIn(**event.data)
            job_search_out = JobSearchOut(
                id=str(uuid.uuid4()),
                job_title=job_search_in.job_title,
                location=job_search_in.location,
                job_types=job_search_in.job_types,
                remote_types=job_search_in.remote_types,
                time_period=job_search_in.time_period,
                user_id=job_search_in.user_id
            )
            
            # Add job search to MongoDB
            await self.add_search(job_search_out)
            
            # Publish processed event
            self.stream_manager.publish(StreamEvent(
                type=StreamType.JOB_SEARCH_PROCESSED,
                data={
                    "job_search": job_search_out.model_dump(mode='json'),
                    "status": "processed"
                },
                source="job_search_manager"
            ))
            
        except Exception as e:
            logger.error(f"Error handling job search addition: {e}")
            self.stream_manager.publish(StreamEvent(
                type=StreamType.SEND_MESSAGE,
                data={
                    "user_id": event.data["user_id"],
                    "message": "Sorry, there was an error creating your job search. Please try again."
                },
                source="job_search_manager"
            ))

    async def _handle_job_search_remove(self, event: StreamEvent):
        """Handle job search removal from Telegram Bot"""
        try:
            # Delete the job search
            success = await self.delete_search(
                search_id=event.data["search_id"],
                user_id=event.data["user_id"]
            )
            
            if success:
                self.stream_manager.publish(StreamEvent(
                    type=StreamType.SEND_MESSAGE,
                    data={
                        "user_id": event.data["user_id"],
                        "message": "Your job search has been removed successfully."
                    },
                    source="job_search_manager"
                ))
            else:
                self.stream_manager.publish(StreamEvent(
                    type=StreamType.SEND_MESSAGE,
                    data={
                        "user_id": event.data["user_id"],
                        "message": "Sorry, we couldn't find the job search to remove."
                    },
                    source="job_search_manager"
                ))
                
        except Exception as e:
            logger.error(f"Error handling job search removal: {e}")
            self.stream_manager.publish(StreamEvent(
                type=StreamType.SEND_MESSAGE,
                data={
                    "user_id": event.data["user_id"],
                    "message": "Sorry, there was an error removing your job search. Please try again."
                },
                source="job_search_manager"
            ))
            