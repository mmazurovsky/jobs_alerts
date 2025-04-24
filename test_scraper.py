"""
Test script for LinkedIn job scraper.
"""
import asyncio
import logging
import sys
from src.core.linkedin_scraper import LinkedInScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_count_jobs():
    """Test the job counting functionality of the LinkedIn scraper."""
    async with LinkedInScraper() as scraper:
        # Initialize browser
        if not await scraper.initialize():
            logger.error("Failed to initialize browser")
            sys.exit(1)

        # Login to LinkedIn
        if not await scraper.login():
            logger.error("Failed to login to LinkedIn")
            sys.exit(1)

        # Search for jobs
        keywords = "python developer"
        location = "remote"
        logger.info(f"Testing job count with keywords: '{keywords}' in location: '{location}'")
        
        # Count the jobs
        job_count = await scraper.count_jobs(keywords, location)
        logger.info(f"Found {job_count} jobs")
        
        # Check if we have enough jobs
        if job_count < 10:
            logger.error(f"Test failed: Expected at least 10 jobs, but found only {job_count}")
            sys.exit(1)
        else:
            logger.info(f"Test passed: Successfully found {job_count} jobs (minimum required: 10)")
            
        return job_count

async def test_scrape_jobs():
    """Test the job scraping functionality of the LinkedIn scraper."""
    async with LinkedInScraper() as scraper:
        # Initialize browser
        if not await scraper.initialize():
            logger.error("Failed to initialize browser")
            sys.exit(1)

        # Login to LinkedIn
        if not await scraper.login():
            logger.error("Failed to login to LinkedIn")
            sys.exit(1)

        # Search for jobs
        keywords = "python developer"
        location = "remote"
        logger.info(f"Testing job scraping with keywords: '{keywords}' in location: '{location}'")
        
        # Scrape the jobs
        jobs = await scraper.scrape_jobs(keywords, location)
        
        # Verify results
        job_count = len(jobs)
        logger.info(f"Successfully scraped {job_count} jobs")
        
        if job_count < 10:
            logger.error(f"Test failed: Expected at least 10 jobs, but scraped only {job_count}")
            sys.exit(1)
        else:
            logger.info(f"Test passed: Successfully scraped {job_count} jobs (minimum required: 10)")

        # Print summary of first 5 jobs
        logger.info("\nFirst 5 jobs found:")
        for i, job in enumerate(jobs[:5], 1):
            print(f"\nJob {i}/{job_count}:")
            print(f"Title: {job['title']}")
            print(f"Company: {job['company']}")
            print(f"Location: {job['location']}")
            if job.get('job_type'):
                print(f"Job Type: {job['job_type']}")
            print("-" * 80)
            
        return jobs

async def test_scraper():
    """Run all tests for the LinkedIn scraper."""
    logger.info("Starting LinkedIn scraper tests...")
    
    # Test job counting
    logger.info("\n=== Testing Job Counting ===")
    job_count = await test_count_jobs()
    
    # Test job scraping
    logger.info("\n=== Testing Job Scraping ===")
    jobs = await test_scrape_jobs()
    
    logger.info("\nAll tests completed successfully!")

if __name__ == "__main__":
    # Only run the job counting test
    asyncio.run(test_count_jobs()) 