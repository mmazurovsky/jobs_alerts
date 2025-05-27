"""
Unit tests for LinkedIn job scraper.
"""
import unittest
import asyncio
import logging
import sys
from src.core.linkedin_scraper import LinkedInScraper
from src.core.config import Config
from src.data.data import StreamManager

# Ensure logging is always visible during pytest runs, even if other modules configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True  # Force reconfiguration so logs always show
)
logger = logging.getLogger(__name__)

class TestLinkedInScraper(unittest.TestCase):
    """Test cases for LinkedInScraper class."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment before running any tests."""
        cls.loop = asyncio.get_event_loop()
        cls.scraper = None
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests are complete."""
        if cls.scraper:
            cls.loop.run_until_complete(cls.scraper.close())
    
    def setUp(self):
        """Set up test environment."""
        self.loop = asyncio.get_event_loop()
        self.scraper = self.loop.run_until_complete(LinkedInScraper.create_new_session(StreamManager(), name="TestLinkedInScraper"))
        self.loop.run_until_complete(self.scraper.login())
    
    def tearDown(self):
        """Clean up after tests."""
        self.loop.run_until_complete(self.scraper.close())
    
    async def async_test_search_jobs(self):
        """Test basic job search functionality."""
        keywords = "Software Engineer"
        location = "San Francisco"
        
        jobs = await self.scraper.search_jobs(
            keywords=keywords,
            location=location
        )
        
        self.assertIsNotNone(jobs)
        self.assertIsInstance(jobs, list)
        self.assertGreater(len(jobs), 0)
        
        # Check job details
        for job in jobs:
            self.assertIsNotNone(job.title)
            self.assertIsNotNone(job.company)
            self.assertIsNotNone(job.location)
            self.assertIsNotNone(job.description)
            self.assertIsNotNone(job.link)
            
            # Verify job details are not empty
            self.assertTrue(job.title)
            self.assertTrue(job.company)
            self.assertTrue(job.location)
            self.assertTrue(job.description)
            self.assertTrue(job.link)
            
            # Verify job link is a valid LinkedIn URL
            self.assertTrue(job.link.startswith('https://www.linkedin.com/jobs/view/'))
            
            # Verify job title contains keywords
            self.assertIn(keywords.lower(), job.title.lower())
            
            # Verify job link is a valid LinkedIn URL
            self.assertTrue(job.link.startswith('https://www.linkedin.com/jobs/view/'))

    def test_search_jobs(self):
        """Run the basic job search test."""
        self.loop.run_until_complete(self.async_test_search_jobs())

if __name__ == '__main__':
    unittest.main() 