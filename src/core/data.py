from dataclasses import dataclass

@dataclass
class JobListing:
    """Class for storing job listing data."""
    title: str
    company: str
    location: str
    description: str
    link: str
    job_type: str
    timestamp: str