import pytest
import asyncio
from src.core.linkedin_scraper_guest import LinkedInScraperGuest
from src.data.data import TimePeriod

@pytest.mark.asyncio
async def test_guest_search_jobs():
    scraper = LinkedInScraperGuest(name="test_guest")
    results = await scraper.search_jobs(
        keywords="software engineer",
        location="USA",
        time_period=TimePeriod.parse("24 hours"),
        max_results=5
    )
    assert results, "No jobs found for guest search!"
    print("First job:", results[0]) 