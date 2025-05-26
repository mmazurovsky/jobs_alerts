import asyncio
import logging
from src.core.linkedin_scraper import LinkedInScraper
from src.data.data import StreamManager

logging.basicConfig(level=logging.INFO)

async def test_login():
    scraper = LinkedInScraper(StreamManager())
    await scraper.initialize()
    login_success = await scraper.login()
    
    if login_success:
        # Verify we're on the feed page
        feed_content = await scraper.page.query_selector('.feed-shared-update-v2')
        if feed_content:
            logging.info("✅ Successfully logged in and reached feed page!")
        else:
            logging.error("❌ Login succeeded but could not find feed content")
    else:
        logging.error("❌ Login failed")
    
    # Keep the script running
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(test_login()) 