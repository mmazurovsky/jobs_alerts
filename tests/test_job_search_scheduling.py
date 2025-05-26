import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from src.data.mongo_manager import MongoManager
from src.schedulers.job_search_scheduler import JobSearchScheduler
from src.user.job_search_manager import JobSearchManager
from src.core.config import config
from src.core.linkedin_scraper import LinkedInScraper
from src.data.data import StreamManager

@pytest_asyncio.fixture
async def mongo_manager():
    manager = MongoManager()
    await manager.connect()
    yield manager

@pytest_asyncio.fixture
async def job_search_scheduler():
    stream_manager = MagicMock(spec=StreamManager)
    scheduler = JobSearchScheduler(stream_manager)
    await scheduler.initialize()
    yield scheduler
    await scheduler.stop()

@pytest_asyncio.fixture
async def job_search_manager(mongo_manager, job_search_scheduler):
    manager = JobSearchManager(mongo_manager, job_search_scheduler)
    await manager.initialize()
    yield manager

@pytest.mark.asyncio
async def test_load_existing_job_searches(mongo_manager, job_search_scheduler, job_search_manager):
    # Get all searches from MongoDB
    mongo_searches = await mongo_manager.get_all_searches()
    
    # Verify searches were loaded into the manager
    for search in mongo_searches:
        user_searches = await job_search_manager.get_user_searches(search.user_id)
        assert any(s.id == search.id for s in user_searches), f"Search {search.id} not found in manager"
        
        # Verify search is scheduled
        assert search.id in job_search_scheduler._active_searches, f"Search {search.id} not scheduled" 