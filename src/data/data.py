"""
Data models and enums for the application.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

class TimePeriod(Enum):
    """Time periods for job search."""
    MINUTES_5 = 300    # 5 minutes
    MINUTES_10 = 600   # 10 minutes
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
        return f"r{this.seconds}"

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
class NewJobSearch:
    """Data for creating a new job search."""
    job_title: str
    location: str
    job_types: List[JobType]
    remote_types: List[RemoteType]
    time_period: TimePeriod
    user_id: int  # Telegram user ID

@dataclass
class JobSearchData:
    """Configuration for a job search."""
    id: str  # Required unique identifier for the job search
    job_title: str
    location: str
    job_types: List[JobType]
    remote_types: List[RemoteType]
    time_period: TimePeriod
    user_id: int  # Telegram user ID
    created_at: datetime
