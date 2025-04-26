"""
Data models and enums for the application.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set

from apscheduler.triggers.cron import CronTrigger

class TimePeriod(Enum):
    """Time periods for job search."""
    MINUTES_5 = 300    # 5 minutes
    MINUTES_15 = 900   # 15 minutes
    MINUTES_30 = 1800  # 30 minutes
    MINUTES_60 = 3600  # 1 hour
    HOURS_4 = 14400    # 4 hours

    @property
    def seconds(self) -> int:
        """Get the time period in seconds."""
        return self.value

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

class JobType(Enum):
    """Types of jobs."""
    FULL_TIME = "Full-time"
    PART_TIME = "Part-time"
    CONTRACT = "Contract"
    TEMPORARY = "Temporary"
    INTERNSHIP = "Internship"

class RemoteType(Enum):
    """Types of remote work."""
    ON_SITE = "On-site"
    REMOTE = "Remote"
    HYBRID = "Hybrid"

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

@dataclass
class JobSearchIn:
    """Data for creating a new job search."""
    job_title: str
    location: str
    job_types: List[JobType]
    remote_types: List[RemoteType]
    time_period: TimePeriod
    user_id: int  # Telegram user ID

@dataclass
class JobSearchOut:
    """Configuration for a job search."""
    id: str  # Required unique identifier for the job search
    job_title: str
    location: str
    job_types: List[JobType]
    remote_types: List[RemoteType]
    time_period: TimePeriod
    user_id: int  # Telegram user ID
    created_at: datetime

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
