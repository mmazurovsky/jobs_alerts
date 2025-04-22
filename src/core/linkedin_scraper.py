"""
LinkedIn job scraper implementation using Playwright.
"""
import asyncio
import logging
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from src.core.config import config

logger = logging.getLogger(__name__)

@dataclass
class JobListing:
    """Class for storing job listing data."""
    title: str
    company: str
    location: str
    description: str
    link: str
    timestamp: str

class LinkedInScraper:
    """LinkedIn job scraper using Playwright."""
    
    def __init__(self):
        """Initialize the scraper."""
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.state_file = Path("linkedin_state.json")
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        
    async def initialize(self):
        """Initialize the browser and page."""
        try:
            self.playwright = await async_playwright().start()
            
            # Launch Chromium with specific settings
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # Make browser visible
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--disable-gpu",
                    "--window-size=1920,1080",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-site-isolation-trials"
                ],
                chromium_sandbox=False
            )
            
            # Create context with essential settings
            context_options = {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "ignore_https_errors": True,
                "java_script_enabled": True,
                "has_touch": False,
                "is_mobile": False,
                "locale": "en-US",
                "timezone_id": "America/New_York",
                "permissions": ["geolocation"]
            }
            
            # Try to load existing state if available
            if self.state_file.exists():
                logger.info("Found existing LinkedIn state - loading...")
                self.context = await self.browser.new_context(**context_options)
                with open(self.state_file, "r") as f:
                    await self.context.add_cookies(eval(f.read()))
            else:
                self.context = await self.browser.new_context(**context_options)
            
            # Create new page
            self.page = await self.context.new_page()
            self.page.set_default_timeout(1000)  # 1 second timeout
            self.page.set_default_navigation_timeout(5000)  # 5 seconds for navigation
            
            logger.info("Browser and page initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize browser: {str(e)}")
            return False
            
    async def login(self) -> bool:
        """Login to LinkedIn using Playwright."""
        try:
            if not self.page:
                logger.error("Browser not initialized")
                return False
                
            # Check existing session
            if self.state_file.exists():
                await self.page.goto("https://www.linkedin.com/feed/")
                await asyncio.sleep(0.5)
                if "feed" in self.page.url:
                    logger.info("Successfully restored LinkedIn session")
                    return True
            
            # Login with credentials
            await self.page.goto("https://www.linkedin.com/login")
            await asyncio.sleep(0.5)
            
            # Fill login form
            await self.page.fill("#username", config.linkedin_email)
            await self.page.fill("#password", config.linkedin_password)
            await self.page.click("button[type='submit']")
            
            # Wait longer for login to complete
            await asyncio.sleep(2)  # Give more time for login redirect
            
            # Check if we're on the feed page or any other LinkedIn page
            if "linkedin.com" in self.page.url and "login" not in self.page.url:
                logger.info("Successfully logged in to LinkedIn")
                
                # Save session state
                if self.context:
                    with open(self.state_file, "w") as f:
                        f.write(str(await self.context.cookies()))
                    logger.info("Saved LinkedIn session state")
                return True
                
            logger.error("Login failed - redirected to unexpected URL")
            return False
                
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False
            
    async def search_jobs(self, keywords: str, location: Optional[str] = None) -> List[Dict[str, str]]:
        """Search for jobs on LinkedIn using the provided keywords and location."""
        if not self.page:
            raise RuntimeError("Browser not initialized")

        try:
            # Navigate to jobs search page with the correct URL
            logger.info("Navigating to LinkedIn jobs search page...")
            await self.page.goto("https://www.linkedin.com/jobs/search/")
            await asyncio.sleep(2)  # Wait for page to stabilize

            # Find and fill the search input - try different selectors for logged-in/out states
            logger.info(f"Searching for jobs with keywords: {keywords}")
            search_selectors = [
                'input[aria-label="Search by title, skill, or company"]',
                'input[aria-label="Search job titles or companies"]',
                '#jobs-search-box-keyword-id-ember'
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = await self.page.wait_for_selector(selector, timeout=2000)
                    if search_input:
                        logger.info(f"Found search input using selector: {selector}")
                        break
                except:
                    continue

            if not search_input:
                raise Exception("Could not find search input field")
            
            await search_input.click()  # Ensure input is focused
            await search_input.fill("")  # Clear existing text
            await search_input.fill(keywords)
            await asyncio.sleep(1)

            # Fill location if provided
            if location:
                logger.info(f"Adding location filter: {location}")
                location_selectors = [
                    'input[aria-label="City, state, or zip code"]',
                    'input[aria-label="Location"]',
                    '#jobs-search-box-location-id-ember'
                ]
                
                location_input = None
                for selector in location_selectors:
                    try:
                        location_input = await self.page.wait_for_selector(selector, timeout=2000)
                        if location_input:
                            logger.info(f"Found location input using selector: {selector}")
                            break
                    except:
                        continue

                if location_input:
                    await location_input.click()  # Ensure input is focused
                    await location_input.fill("")  # Clear existing text
                    await location_input.fill(location)
                    await asyncio.sleep(1)
                else:
                    logger.warning("Could not find location input field")

            # Try different search button selectors
            logger.info("Looking for search button...")
            search_button_selectors = [
                'button.jobs-search-box__submit-button.artdeco-button.artdeco-button--2.artdeco-button--secondary',
                '#global-nav-search button.jobs-search-box__submit-button',
                'button.jobs-search-box__submit-button[type="button"]'
            ]
            
            search_button = None
            for selector in search_button_selectors:
                try:
                    search_button = await self.page.wait_for_selector(selector, timeout=2000, state="visible")
                    if search_button:
                        logger.info(f"Found search button using selector: {selector}")
                        break
                except:
                    continue

            if not search_button:
                # If no button found, try pressing Enter in the search input
                logger.info("No search button found, trying to submit with Enter key")
                await search_input.press("Enter")
            else:
                logger.info("Clicking search button...")
                await search_button.click()
            
            await asyncio.sleep(2)  # Wait for search to initiate
            
            # Wait for results with increased timeout
            logger.info("Waiting for search results...")
            results_selectors = [
                'div[data-job-id]',  # This matches the job card container
                '.jobs-search-results-list__list-item--active',
                '.job-card-list'
            ]
            
            results_list = None
            for selector in results_selectors:
                try:
                    results_list = await self.page.wait_for_selector(selector, timeout=5000)
                    if results_list:
                        logger.info(f"Found results list using selector: {selector}")
                        break
                except:
                    continue

            if not results_list:
                logger.error("Could not find results list")
                return []

            await asyncio.sleep(3)  # Additional wait for dynamic content

            # Get all job listings using the data-job-id attribute
            job_cards = await self.page.query_selector_all('div[data-job-id]')
            logger.info(f"Found {len(job_cards)} job listings")

            jobs = []
            for card in job_cards:
                try:
                    # Extract job details directly from the card
                    title_elem = await card.query_selector('a[href*="/jobs/view/"]')
                    if not title_elem:
                        logger.warning("Could not find job title link")
                        continue

                    # Get the title text
                    title = await title_elem.inner_text()
                    title = title.split('\n')[0].strip()  # Take only the first line

                    # Get company name from the subtitle
                    company_elem = await card.query_selector('.artdeco-entity-lockup__subtitle')
                    company = await company_elem.inner_text() if company_elem else ""

                    # Get location from the metadata wrapper
                    location_elem = await card.query_selector('.job-card-container__metadata-wrapper')
                    location = await location_elem.inner_text() if location_elem else ""

                    # Get the job link and make it absolute
                    link = await title_elem.get_attribute('href')
                    if link and not link.startswith('http'):
                        link = f"https://www.linkedin.com{link}"

                    # Get job description
                    logger.info(f"Clicking job link: {title}")
                    print(f"\nWaiting 3 seconds before clicking the job card for: {title}")
                    await asyncio.sleep(3)  # Add delay before clicking
                    await title_elem.click()
                    await asyncio.sleep(2)  # Wait for job details to load
                    
                    # Wait for and extract job details from the details page
                    description_elem = await self.page.wait_for_selector('.jobs-description__content', timeout=5000)
                    description = await description_elem.inner_text() if description_elem else "No description available"

                    # Get additional job details and clean up the text
                    job_type_elem = await self.page.query_selector('.job-details-jobs-unified-top-card__job-insight')
                    job_type = ""
                    if job_type_elem:
                        job_type = await job_type_elem.inner_text()
                        # Clean up the job type text
                        job_type = job_type.replace('Matches your job preferences, workplace type is ', '')
                        job_type = job_type.replace('Matches your job preferences, job type is ', '')
                        job_type = ' • '.join([t.strip() for t in job_type.split('\n') if t.strip()])

                    # Print job details immediately after processing
                    print("\n" + "=" * 80)
                    print(f"📌 {title.strip()}")
                    print(f"🏢 {company.strip()}")
                    print(f"📍 {location.strip()}")
                    if job_type:
                        print(f"💼 {job_type}")
                    print(f"🔗 {link}")
                    print("\n📝 Full Description:")
                    print("-" * 80)
                    print(description.strip())
                    print("-" * 80)
                    print("\nWaiting 5 seconds before processing next job...")
                    await asyncio.sleep(5)

                    jobs.append({
                        'title': title.strip(),
                        'company': company.strip(),
                        'location': location.strip(),
                        'description': description.strip(),
                        'link': link,
                        'job_type': job_type
                    })
                    logger.info(f"Processed job: {title} at {company}")

                except Exception as e:
                    logger.error(f"Error processing job card: {str(e)}")
                    continue

            return jobs

        except Exception as e:
            logger.error(f"Error during job search: {str(e)}")
            return []
            
    async def close(self):
        """Close the browser and cleanup."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None










