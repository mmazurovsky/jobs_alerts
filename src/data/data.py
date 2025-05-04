"""
Data models and enums for the application.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field
from rx.subject import Subject

from apscheduler.triggers.cron import CronTrigger

class TimePeriod(Enum):
    """Time periods for job search."""
    MINUTES_5 = (300, "5 minutes")    # 5 minutes
    MINUTES_15 = (900, "15 minutes")   # 15 minutes
    MINUTES_30 = (1800, "30 minutes")  # 30 minutes
    MINUTES_60 = (3600, "1 hour")      # 1 hour
    HOURS_4 = (14400, "4 hours")       # 4 hours

    def __init__(self, seconds: int, display_name: str):
        self._seconds = seconds
        self._display_name = display_name

    @property
    def seconds(self) -> int:
        """Get the time period in seconds."""
        return self._seconds

    @property
    def display_name(self) -> str:
        """Get the human-readable display name."""
        return self._display_name

    @property
    def f_tpr_param(self) -> str:
        """Get the f_TPR parameter value for LinkedIn URL."""
        return f"r{self.seconds}"
    
    def get_cron_trigger(self) -> CronTrigger:
        """Get the appropriate APScheduler CronTrigger for this time period."""
        if self == TimePeriod.MINUTES_5:
            # Run at 00, 05, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55 minutes of each hour
            return CronTrigger(minute='0,5,10,15,20,25,30,35,40,45,50,55')
        elif self == TimePeriod.MINUTES_15:
            # Run at 00, 15, 30, 45 minutes of each hour
            return CronTrigger(minute='0,15,30,45')
        elif self == TimePeriod.MINUTES_30:
            # Run at 00 and 30 minutes of each hour
            return CronTrigger(minute='0,30')
        elif self == TimePeriod.MINUTES_60:
            # Run at the top of each hour
            return CronTrigger(minute='0')
        elif self == TimePeriod.HOURS_4:
            # Run at 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
            return CronTrigger(hour='0,4,8,12,16,20', minute='0')
        else:
            # Default to running every 15 minutes
            return CronTrigger(minute='0,15,30,45')

    @classmethod
    def parse(cls, value: str) -> 'TimePeriod':
        """Parse a string value to TimePeriod enum.
        
        Args:
            value: String value to parse (e.g., "5 minutes", "MINUTES_5")
            
        Returns:
            TimePeriod enum value
            
        Raises:
            ValueError: If the value cannot be parsed
        """
            
        # Try matching against display names
        for time_period in cls:
            if value.lower() == time_period.display_name.lower():
                return time_period
                
        raise ValueError(f"Invalid time period: {value}")

class JobType(Enum):
    """Types of jobs."""
    FULL_TIME = "Full-time"
    PART_TIME = "Part-time"
    CONTRACT = "Contract"
    TEMPORARY = "Temporary"
    INTERNSHIP = "Internship"

    @classmethod
    def parse(cls, value: str) -> 'JobType':
        """Parse a string value to JobType enum.
        
        Args:
            value: String value to parse (e.g., "Full-time", "FULL_TIME")
            
        Returns:
            JobType enum value
            
        Raises:
            ValueError: If the value cannot be parsed
        """
            
        # Try matching against display values
        for job_type in cls:
            if value.lower() == job_type.value.lower():
                return job_type
                
        raise ValueError(f"Invalid job type: {value}")

class RemoteType(Enum):
    """Types of remote work."""
    ON_SITE = "On-site"
    REMOTE = "Remote"
    HYBRID = "Hybrid"

    @classmethod
    def parse(cls, value: str) -> 'RemoteType':
        """Parse a string value to RemoteType enum.
        
        Args:
            value: String value to parse (e.g., "Remote", "REMOTE")
            
        Returns:
            RemoteType enum value
            
        Raises:
            ValueError: If the value cannot be parsed
        """
            
        # Try matching against display values
        for remote_type in cls:
            if value.lower() == remote_type.value.lower():
                return remote_type
                
        raise ValueError(f"Invalid remote type: {value}")

@dataclass
class JobListing:
    """LinkedIn job listing data."""
    title: str
    company: str
    location: str
    description: str
    link: str
    job_type: str
    timestamp: str

class JobSearchRemove(BaseModel):
    """Data for removing a job search from Telegram bot."""
    user_id: int
    search_id: str

class JobSearchIn(BaseModel):
    """Data for creating a new job search."""
    job_title: str
    location: str
    job_types: List[JobType]
    remote_types: List[RemoteType]
    time_period: TimePeriod
    user_id: int  # Telegram user ID

class JobSearchOut(BaseModel):
    """Configuration for a job search."""
    id: str = Field(..., description="Required unique identifier for the job search")
    job_title: str
    location: str
    job_types: List[JobType]
    remote_types: List[RemoteType]
    time_period: TimePeriod
    user_id: int  # Telegram user ID
    created_at: datetime = Field(default_factory=datetime.now)

class SentJobsTracker:
    """Tracks which jobs have been sent to users to prevent duplicates."""
    def __init__(self):
        self._sent_jobs: Dict[int, Set[str]] = {}  # user_id -> set of job links

    def mark_job_sent(self, user_id: int, job_link: str) -> None:
        """Mark a job as sent to a user."""
        if user_id not in self._sent_jobs:
            self._sent_jobs[user_id] = set()
        self._sent_jobs[user_id].add(job_link)

    def is_job_sent(self, user_id: int, job_link: str) -> bool:
        """Check if a job has already been sent to a user."""
        return user_id in self._sent_jobs and job_link in self._sent_jobs[user_id]

    def clear_user_jobs(self, user_id: int) -> None:
        """Clear the sent jobs history for a user."""
        if user_id in self._sent_jobs:
            del self._sent_jobs[user_id]

    def clear_all(self) -> None:
        """Clear all sent jobs history."""
        self._sent_jobs.clear()

class StreamType(Enum):
    """Types of events in the stream."""
    JOB_SEARCH_ADD = "job_search_add"
    JOB_SEARCH_REMOVE = "job_search_remove"
    JOB_SEARCH_PROCESSED = "job_search_processed"
    SEND_MESSAGE = "send_message"
    INITIAL_JOB_SEARCHES = "initial_job_searches"

@dataclass
class StreamEvent:
    type: StreamType
    data: dict
    source: str

class StreamManager:
    def __init__(self):
        self.streams: Dict[StreamType, Subject] = {
            StreamType.JOB_SEARCH_ADD: Subject(),
            StreamType.JOB_SEARCH_REMOVE: Subject(),
            StreamType.JOB_SEARCH_PROCESSED: Subject(),
            StreamType.SEND_MESSAGE: Subject(),
            StreamType.INITIAL_JOB_SEARCHES: Subject()
        }
    
    def get_stream(self, stream_type: StreamType) -> Subject:
        return self.streams[stream_type]
    
    def publish(self, event: StreamEvent):
        self.streams[event.type].on_next(event)
