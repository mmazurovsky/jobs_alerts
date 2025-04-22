import asyncio
from src.core.linkedin_scraper import LinkedInScraper

async def main():
    async with LinkedInScraper() as scraper:
        # Login to LinkedIn
        if not await scraper.login():
            print("Failed to login to LinkedIn")
            return

        # Search for jobs
        jobs = await scraper.search_jobs(
            keywords="Software Engineer",
            location="San Francisco"
        )

        # Print summary
        print(f"\n{'=' * 40} Summary {'=' * 40}")
        print(f"Total jobs found: {len(jobs)}")
        print("\nJobs processed:")
        for i, job in enumerate(jobs, 1):
            print(f"{i}. {job['title']} at {job['company']}")

if __name__ == "__main__":
    asyncio.run(main()) 