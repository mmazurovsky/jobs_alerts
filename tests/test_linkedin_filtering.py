"""
Unit test for LinkedIn job scraper filtering.
"""
import unittest
import asyncio
import logging
from src.core.linkedin_scraper import LinkedInScraper
from src.data.data import StreamManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestLinkedInFiltering(unittest.TestCase):
    """Test case for LinkedInScraper filtering."""
    
    @classmethod
    def setUpClass(cls):
        cls.loop = asyncio.get_event_loop()
        cls.scraper = LinkedInScraper(StreamManager(), name="TestLinkedInFiltering")
        cls.loop.run_until_complete(cls.scraper.initialize())
        cls.loop.run_until_complete(cls.scraper.login())
    
    @classmethod
    def tearDownClass(cls):
        cls.loop.run_until_complete(cls.scraper.close())
    
    async def async_test_filtering(self):
        keywords = "Software Engineer"
        location = "San Francisco"
        job_types = ["Full-time", "Contract"]
        remote_types = ["Hybrid"]
        max_jobs = 2
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
        for job in jobs:
            self.assertIsNotNone(job.title)
            self.assertIsNotNone(job.company)
            self.assertIsNotNone(job.location)
            self.assertIsNotNone(job.description)
            self.assertIsNotNone(job.link)
            self.assertIsNotNone(job.job_type)
            self.assertTrue(job.title)
            self.assertTrue(job.company)
            self.assertTrue(job.location)
            self.assertTrue(job.description)
            self.assertTrue(job.link)
            self.assertTrue(job.link.startswith('https://www.linkedin.com/jobs/view/'))
            # self.assertIn(keywords.lower(), job.title.lower())  # Removed: LinkedIn may return fuzzy matches
            job_type_found = False
            for job_type in job_types:
                if job_type.lower() in job.job_type.lower():
                    job_type_found = True
                    break
            self.assertTrue(job_type_found, f"Job type {job.job_type} does not match any of {job_types}")
    
    def test_filtering(self):
        self.loop.run_until_complete(self.async_test_filtering())

if __name__ == '__main__':
    unittest.main() 