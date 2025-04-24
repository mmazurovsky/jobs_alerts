"""
Unit tests for LinkedIn job scraper.
"""
import unittest
import asyncio
import logging
from src.core.linkedin_scraper import LinkedInScraper
from src.core.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
        self.scraper = LinkedInScraper()
        self.loop = asyncio.get_event_loop()
        # Initialize browser and log in
        self.loop.run_until_complete(self.scraper.initialize())
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

    async def async_test_filtering(self):
        """Test job search with filters."""
        keywords = "Software Engineer"
        location = "San Francisco"
        job_types = ["Full-time", "Contract"]
        remote_types = ["Hybrid"]
        max_jobs = 2  # Limit to 2 jobs
        
        jobs = await self.scraper.search_jobs(
            keywords=keywords,
            location=location,
            job_types=job_types,
            remote_types=remote_types,
            max_jobs=max_jobs,
            max_pages=1,
        )
        
        self.assertIsNotNone(jobs)
        self.assertIsInstance(jobs, list)
        self.assertEqual(len(jobs), max_jobs, f"Expected exactly {max_jobs} jobs, but got {len(jobs)}")
        
        # Check job details
        for job in jobs:
            self.assertIsNotNone(job.title)
            self.assertIsNotNone(job.company)
            self.assertIsNotNone(job.location)
            self.assertIsNotNone(job.description)
            self.assertIsNotNone(job.link)
            self.assertIsNotNone(job.job_type)
            
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
            
            # Verify job type matches one of the requested types
            job_type_found = False
            for job_type in job_types:
                if job_type.lower() in job.job_type.lower():
                    job_type_found = True
                    break
            self.assertTrue(job_type_found, f"Job type {job.job_type} does not match any of {job_types}")

    def test_filtering(self):
        """Run the job search with filters test."""
        self.loop.run_until_complete(self.async_test_filtering())

if __name__ == '__main__':
    unittest.main() 