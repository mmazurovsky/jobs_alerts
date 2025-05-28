import pytest
import asyncio
from src.core.linkedin_scraper_guest import LinkedInScraperGuest
from src.data.data import TimePeriod
from src.data.data import JobType, RemoteType
import logging
from pathlib import Path
from src.utils.logging_config import setup_logging

# Ensure logs are written to logs/app.log during test runs
setup_logging(log_file=Path('logs/app.log'))

@pytest.mark.asyncio
async def test_guest_search_jobs():
    scraper = LinkedInScraperGuest(name="test_guest")
    results = await scraper.search_jobs(
        keywords="software engineer",
        location="USA",
        time_period=TimePeriod.parse("24 hours"),
        max_results=None,
        job_types=[JobType.parse("Full-time")],
        remote_types=[RemoteType.parse("Remote")]
    )
    assert results, "No jobs found for guest search!"
    print(f"\nTotal jobs returned: {len(results)}")
    for idx, job in enumerate(results, 1):
        print(f"Job {idx}: {job}") 