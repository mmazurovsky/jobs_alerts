"""
Data models and enums for the application.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from pydantic import BaseModel, Field, field_validator
from rx.subject import Subject
import logging
import re

from apscheduler.triggers.cron import CronTrigger

from shared.util.other_util import enable_enum_name_deserialization

logger = logging.getLogger(__name__)


from apscheduler.triggers.cron import CronTrigger

class TimePeriod:
    _instances = {}

    def __init__(self, display_name: str, seconds: int, cron: CronTrigger):
        self.display_name = display_name
        self._seconds = seconds
        self._cron = cron
        TimePeriod._instances[display_name.lower()] = self

    @property
    def seconds(self):
        return self._seconds

    def get_cron_trigger(self):
        return self._cron

    def to_human_readable(self):
        return self.display_name

    def to_seconds(self):
        return self.seconds
    
    @classmethod
    def __get_validators__(cls):
        yield cls.parse

    @classmethod
    def parse(cls, value: str, *args, **kwargs):
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            instance = cls._instances.get(value.strip().lower())
            if not instance:
                raise ValueError(f"Invalid time period: {value}, {args}, {kwargs}")
            return instance
        raise ValueError(f"TimePeriod.parse expects a string or TimePeriod instance, got {type(value)}")

    def __eq__(self, other):
        return isinstance(other, TimePeriod) and self.display_name == other.display_name

    def __repr__(self):
        return f"<TimePeriod '{self.display_name}'>"

TimePeriod("5 minutes", 300, CronTrigger(minute='0,5,10,15,20,25,30,35,40,45,50,55'))
TimePeriod("10 minutes", 600, CronTrigger(minute='0,10,20,30,40,50'))
TimePeriod("15 minutes", 900, CronTrigger(minute='0,15,30,45'))
TimePeriod("20 minutes", 1200, CronTrigger(minute='0,20,40'))
TimePeriod("30 minutes", 1800, CronTrigger(minute='0,30'))
TimePeriod("1 hour", 3600, CronTrigger(minute='0'))
TimePeriod("4 hours", 14400, CronTrigger(hour='0,4,8,12,16,20', minute='0'))
TimePeriod("24 hours", 43200, CronTrigger(hour='0', minute='0'))

class JobType:
    _instances = {}

    def __init__(self, label: str):
        self.label = label
        JobType._instances[label.lower()] = self

    @classmethod
    def __get_validators__(cls):
        yield cls.parse

    @classmethod
    def parse(cls, value: str, *args, **kwargs):
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            instance = cls._instances.get(value.strip().lower())
            if not instance:
                raise ValueError(f"Invalid job type: {value}, {args}, {kwargs}")
            return instance
        raise ValueError(f"JobType.parse expects a string or JobType instance, got {type(value)}")

    def __eq__(self, other):
        return isinstance(other, JobType) and self.label == other.label

    def __repr__(self):
        return f"<JobType '{self.label}'>"

# Human-readable instances
JobType("Full-time")
JobType("Part-time")
JobType("Contract")
JobType("Temporary")
JobType("Internship")

class RemoteType:
    _instances = {}

    def __init__(self, label: str):
        self.label = label
        RemoteType._instances[label.lower()] = self

    @classmethod
    def __get_validators__(cls):
        yield cls.parse

    @classmethod
    def parse(cls, value: str, *args, **kwargs):
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            instance = cls._instances.get(value.strip().lower())
            if not instance:
                raise ValueError(f"Invalid remote type: {value}, {args}, {kwargs}")
            return instance
        raise ValueError(f"RemoteType.parse expects a string or RemoteType instance, got {type(value)}")

    def __eq__(self, other):
        return isinstance(other, RemoteType) and self.label == other.label

    def __repr__(self):
        return f"<RemoteType '{self.label}'>"


# Human-readable instances
RemoteType("On-site")
RemoteType("Remote")
RemoteType("Hybrid")


class CustomBaseModel(BaseModel):
    """Base model with custom JSON encoders and decoders."""
    model_config = {
        "use_enum_values": False,  # Use enum names instead of values
        "populate_by_name": True,  # Allow population by field names
        "json_encoders": {
            datetime: lambda v: v.isoformat(),  # Serialize datetime as ISO format
            JobType: lambda v: v.label,
            RemoteType: lambda v: v.label,
            TimePeriod: lambda v: v.display_name
        }
    }

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

class ShortJobListing(CustomBaseModel):
    title: str
    company: str
    location: str
    link: str
    created_ago: str

class JobSearchRemove(CustomBaseModel):
    """Data for removing a job search from Telegram bot."""
    user_id: int
    search_id: str

class JobSearchIn(CustomBaseModel):
    """Data for creating a new job search."""
    job_title: str
    location: str
    job_types: List[JobType]
    remote_types: List[RemoteType]
    time_period: TimePeriod
    user_id: int  # Telegram user ID
    blacklist: List[str] = []  # List of strings to blacklist from job titles

    @field_validator('job_types', 'remote_types', 'time_period')
    @classmethod
    def validate_enums(cls, v):
        """Validate that enum values are properly handled."""
        if isinstance(v, list):
            return [item.name if isinstance(item, Enum) else item for item in v]
        return v.name if isinstance(v, Enum) else v

    model_config = {
        "use_enum_values": True,  # Use enum values instead of names
        "populate_by_name": True,  # Allow population by field names
        "json_encoders": {
            Enum: lambda v: v.name,  # Serialize enums as their names
            datetime: lambda v: v.isoformat()  # Serialize datetime as ISO format
        }
    }

@dataclass
class UserSubscription:
    user_id: int
    subscription_type: str  # "trial", "premium_week", "premium_month"
    start_date: datetime
    end_date: datetime
    is_active: bool
    telegram_payment_charge_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def model_dump(self, mode: str = "python") -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        data = {
            "user_id": self.user_id,
            "subscription_type": self.subscription_type,
            "start_date": self.start_date.isoformat() if mode == "json" else self.start_date,
            "end_date": self.end_date.isoformat() if mode == "json" else self.end_date,
            "is_active": self.is_active,
            "telegram_payment_charge_id": self.telegram_payment_charge_id,
            "created_at": self.created_at.isoformat() if mode == "json" else self.created_at,
            "updated_at": self.updated_at.isoformat() if mode == "json" else self.updated_at,
        }
        return data

@dataclass 
class PaymentTransaction:
    user_id: int
    transaction_id: str
    amount_stars: int
    subscription_type: str
    status: str  # "pending", "processing", "completed", "failed", "refunded"
    telegram_payment_charge_id: Optional[str] = None
    invoice_payload: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def model_dump(self, mode: str = "python") -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        data = {
            "user_id": self.user_id,
            "transaction_id": self.transaction_id,
            "amount_stars": self.amount_stars,
            "subscription_type": self.subscription_type,
            "status": self.status,
            "telegram_payment_charge_id": self.telegram_payment_charge_id,
            "invoice_payload": self.invoice_payload,
            "created_at": self.created_at.isoformat() if mode == "json" else self.created_at,
            "updated_at": self.updated_at.isoformat() if mode == "json" else self.updated_at,
        }
        return data

@dataclass
class JobSearchOut:
    id: str
    job_title: str
    location: str
    job_types: List[JobType]
    remote_types: List[RemoteType]
    time_period: TimePeriod
    user_id: int
    blacklist: List[str]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True  # NEW FIELD: Whether job search is active

    def model_dump(self, mode: str = "python") -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        data = {
            "id": self.id,
            "job_title": self.job_title,
            "location": self.location,
            "job_types": [jt.name for jt in self.job_types] if mode == "json" else [jt.name for jt in self.job_types],
            "remote_types": [rt.name for rt in self.remote_types] if mode == "json" else [rt.name for rt in self.remote_types],
            "time_period": self.time_period.name if mode == "json" else self.time_period.name,
            "user_id": self.user_id,
            "blacklist": self.blacklist,
            "created_at": self.created_at.isoformat() if mode == "json" else self.created_at,
            "is_active": self.is_active,
        }
        return data

    def to_log_string(self) -> str:
        job_types_str = ", ".join([jt.label for jt in self.job_types])
        remote_types_str = ", ".join([rt.label for rt in self.remote_types])
        return f"Job Search {self.id}: '{self.job_title}' in '{self.location}' | Types: {job_types_str} | Remote: {remote_types_str} | Frequency: {self.time_period.display_name} | Active: {self.is_active}"

class StreamType(Enum):
    """Types of events in the stream."""
    SEND_MESSAGE = "send_message"
    SEND_LOG = "send_log"

@dataclass
class StreamEvent:
    type: StreamType
    data: Any
    source: str

class StreamManager:
    def __init__(self):
        self.streams: Dict[StreamType, Subject] = {
            StreamType.SEND_MESSAGE: Subject(),
            StreamType.SEND_LOG: Subject(),
        }
    
    def get_stream(self, stream_type: StreamType) -> Subject:
        return self.streams[stream_type]
    
    def publish(self, event: StreamEvent):
        self.streams[event.type].on_next(event)

def job_types_list() -> str:
    return "\n".join(f"• {job_type.label}" for job_type in JobType._instances.values())

def remote_types_list() -> str:
    return "\n".join(f"• {remote_type.label}" for remote_type in RemoteType._instances.values())

def time_periods_list() -> str:
    return "\n".join(f"• {period.display_name}" for period in TimePeriod._instances.values())

class SentJobOut(CustomBaseModel):
    user_id: int
    job_url: str
    sent_at: datetime

class SearchJobsParams(BaseModel):
    keywords: str = Field(..., min_length=1)
    location: str = Field(..., min_length=1)
    time_period: str = Field(..., min_length=1)
    job_types: list[str] = Field(default_factory=list)
    remote_types: list[str] = Field(default_factory=list)

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_job_type
        yield cls.validate_remote_type

    @classmethod
    def validate_job_type(cls, v):
        if isinstance(v, str):
            return [v]
        return v

    @classmethod
    def validate_remote_type(cls, v):
        if isinstance(v, str):
            return [v]
        return v
