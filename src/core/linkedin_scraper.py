"""
LinkedIn job scraper implementation using Playwright.
"""
import asyncio
import logging
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, Page, Browser, BrowserContext, ElementHandle

from src.core.config import config
from src.data.data import JobListing, TimePeriod

logger = logging.getLogger(__name__)

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
                await self.page.goto("https://www.linkedin.com/feed/", timeout=30000)  # Increased timeout
                await asyncio.sleep(2)  # Increased wait time
                if "feed" in self.page.url:
                    logger.info("Successfully restored LinkedIn session")
                    return True
            
            # Login with credentials
            await self.page.goto("https://www.linkedin.com/login", timeout=30000)  # Increased timeout
            await asyncio.sleep(2)  # Increased wait time
            
            # Fill login form
            await self.page.fill("#username", config.linkedin_email)
            await self.page.fill("#password", config.linkedin_password)
            await self.page.click("button[type='submit']")
            
            # Wait longer for login to complete
            await asyncio.sleep(5)  # Increased wait time
            
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
            
    async def _navigate_to_jobs_page(self, time_period_seconds: Optional[int] = None):
        """Navigate to LinkedIn jobs search page.
        
        Args:
            time_period_seconds: Optional time period in seconds to filter jobs by
        """
        logger.info("Navigating to LinkedIn jobs search page...")
        base_url = "https://www.linkedin.com/jobs/search/"
        
        # Add time period filter to URL if provided
        if time_period_seconds:
            base_url += f"?f_TPR=r{time_period_seconds}"
            
        await self.page.goto(base_url)
        await asyncio.sleep(1.5)  # Wait for page to stabilize

    async def _fill_search_inputs(self, keywords: str, location: Optional[str] = None):
        """Fill in the search inputs with keywords and location."""
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
        await asyncio.sleep(0.5)

        if location:
            await self._fill_location_input(location)

    async def _fill_location_input(self, location: str):
        """Fill in the location input field."""
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
            await asyncio.sleep(0.5)
        else:
            logger.warning("Could not find location input field")

    async def _click_search_button(self):
        """Click the search button or submit with Enter key."""
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
            await self.page.keyboard.press("Enter")
        else:
            logger.info("Clicking search button...")
            await search_button.click()
        
        # Wait for navigation and network idle
        try:
            await self.page.wait_for_load_state("networkidle", timeout=5000)
            logger.info("Page reached network idle state")
        except Exception as e:
            logger.warning(f"Timeout waiting for network idle: {str(e)}")
        
        await asyncio.sleep(1.5)  # Wait for search to initiate

    async def _wait_for_job_search_results(self, max_jobs: Optional[int] = None) -> List[ElementHandle]:
        """Wait for job search results to load and scroll to load all jobs.
        
        Args:
            max_jobs: Optional maximum number of jobs to load. If provided, will stop scrolling once this many jobs are found.
        
        Returns:
            List of job card elements
        """
        logger.info("Waiting for job search results to load...")
        
        # Wait for the job cards container - try multiple selectors
        container_selectors = [
            "div.jobs-search-results-list",
            "div.scaffold-layout__list",
            "div.jobs-search-results-list__list",
            "#main > div > div.scaffold-layout__list-detail-inner.scaffold-layout__list-detail-inner--grow > div.scaffold-layout__list > div"
        ]
        
        job_cards_container = None
        for selector in container_selectors:
            try:
                job_cards_container = await self.page.wait_for_selector(
                    selector,
                    timeout=5000,
                    state="visible"
                )
                if job_cards_container:
                    logger.info(f"Found job cards container using selector: {selector}")
                    break
            except Exception as e:
                continue
                
        if not job_cards_container:
            logger.warning("Could not find job cards container with any selector")
            return []

        # Wait for initial job cards to load
        await asyncio.sleep(2)
        
        job_cards = []
        seen_job_ids = set()  # Track seen job IDs
        last_height = 0
        scroll_attempts = 0
        max_scroll_attempts = 10
        
        while scroll_attempts < max_scroll_attempts:
            # Get current job cards
            current_cards = await self.page.query_selector_all("div.job-card-container")
            logger.info(f"Found {len(current_cards)} job cards in current view")
            
            # Update job cards list with new unique cards
            for card in current_cards:
                try:
                    # Get the job ID from the card
                    title_link = await card.query_selector('a.job-card-list__title--link')
                    if not title_link:
                        continue
                        
                    href = await title_link.get_attribute('href')
                    if not href or '/jobs/view/' not in href:
                        continue
                        
                    job_id = href.split('/jobs/view/')[1].split('/')[0].split('?')[0]
                    
                    # Only add the card if we haven't seen this job ID before
                    if job_id not in seen_job_ids:
                        seen_job_ids.add(job_id)
                        job_cards.append(card)
                        logger.info(f"Added new unique job card with ID: {job_id}")
                except Exception as e:
                    logger.warning(f"Error extracting job ID from card: {e}")
                    continue
                    
            logger.info(f"Total unique job cards found: {len(job_cards)}")
                    
            # Check if we have enough jobs
            if max_jobs is not None and len(job_cards) >= max_jobs:
                logger.info(f"Found {len(job_cards)} jobs, stopping scroll")
                break
                
            # Scroll to bottom of container
            current_height = await job_cards_container.evaluate("element => element.scrollHeight")
            await job_cards_container.evaluate(f"element => element.scrollTo(0, {current_height})")
            
            # Wait for new content to load
            await asyncio.sleep(1)
            
            # Check if we've reached the bottom
            new_height = await job_cards_container.evaluate("element => element.scrollHeight")
            if new_height == last_height:
                scroll_attempts += 1
                logger.info(f"Reached bottom of page (attempt {scroll_attempts}/{max_scroll_attempts})")
            else:
                scroll_attempts = 0
                last_height = new_height
                
        logger.info(f"Final count: Found {len(job_cards)} unique job cards after scrolling")
        return job_cards[:max_jobs] if max_jobs is not None else job_cards

    async def _extract_job_details(self, card) -> Optional[JobListing]:
        """Extract details from a single job card."""
        try:
            # Extract job details directly from the card
            title_elem = await card.query_selector('a[href*="/jobs/view/"]')
            if not title_elem:
                logger.warning("Could not find job title link")
                return None

            # Get the title text
            title = await title_elem.inner_text()
            title = title.split('\n')[0].strip()  # Take only the first line

            # Get company name from the subtitle
            company_elem = await card.query_selector('.artdeco-entity-lockup__subtitle')
            company = await company_elem.inner_text() if company_elem else ""

            # Get location from the metadata wrapper
            location_elem = await card.query_selector('.job-card-container__metadata-wrapper')
            location = await location_elem.inner_text() if location_elem else ""

            # Get job description
            logger.info(f"Clicking job link: {title}")
            print(f"\nWaiting 1.5 seconds before clicking the job card for: {title}")
            await asyncio.sleep(1.5)  # Add delay before clicking
            
            # Click the job card
            await title_elem.click()
            await asyncio.sleep(1)
            
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

            # Get the job link from the job title element
            try:
                # Find the job title link in the card
                title_link = await card.query_selector('a.job-card-list__title--link')
                if not title_link:
                    logger.error("Could not find job title link")
                    return None
                
                # Get the href attribute which contains the job ID
                href = await title_link.get_attribute('href')
                if not href:
                    logger.error("Could not find href attribute in job title link")
                    return None
                
                # Extract job ID from the href
                if '/jobs/view/' in href:
                    job_id = href.split('/jobs/view/')[1].split('/')[0].split('?')[0]
                    logger.info(f"Extracted job ID: {job_id}")
                    
                    # Construct the full job URL
                    job_url = f"https://www.linkedin.com/jobs/view/{job_id}"
                    logger.info(f"Constructed job URL: {job_url}")
                    
                    return JobListing(
                        title=title.strip(),
                        company=company.strip(),
                        location=location.strip(),
                        description=description.strip(),
                        link=job_url,
                        job_type=job_type,
                        timestamp=datetime.now().isoformat()
                    )
                else:
                    logger.error(f"Invalid job link format in href: {href}")
                    return None
                
            except Exception as e:
                logger.error(f"Error getting job link: {str(e)}")
                return None

            # Print job details immediately after processing
            print("\n" + "=" * 80)
            print(f"📌 {title.strip()}")
            print(f"🏢 {company.strip()}")
            print(f"📍 {location.strip()}")
            if job_type:
                print(f"💼 {job_type}")
            print(f"🔗 {href}")
            print("\n📝 Full Description:")
            print("-" * 80)
            print(description.strip())
            print("-" * 80)

            return JobListing(
                title=title.strip(),
                company=company.strip(),
                location=location.strip(),
                description=description.strip(),
                link=href,
                job_type=job_type,
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Error processing job card: {str(e)}")
            return None

    async def _click_next_page(self) -> bool:
        """Click the next page button if available."""
        try:
            # Wait for the next button to be visible
            next_button = await self.page.wait_for_selector(
                'button[aria-label="View next page"]',
                timeout=2000,
                state="visible"
            )
            
            if next_button:
                # Check if the button is disabled
                is_disabled = await next_button.get_attribute("disabled")
                if is_disabled:
                    logger.info("Next page button is disabled - reached last page")
                    return False
                
                # Click the next button
                await next_button.click()
                await asyncio.sleep(2)  # Wait for page load
            return True
                
        except Exception as e:
            logger.info(f"No next page button found or error: {str(e)}")
            return False

    async def _apply_filters(self, job_types=None, remote_types=None):
        """Apply job type and remote type filters to the search results."""
        try:
            # Click the "All filters" button to open the filter panel
            all_filters_button = await self.page.wait_for_selector(
                'button[aria-label="Show all filters. Clicking this button displays all available filter options."]',
                timeout=5000,
                state="visible"
            )
            
            if not all_filters_button:
                logger.error("Could not find 'All filters' button")
                return False
                
            await all_filters_button.click()
            await asyncio.sleep(1.5)  # Wait for filter panel to open
            
            # Find the modal content container
            modal_content = await self.page.wait_for_selector(
                '.artdeco-modal__content',
                timeout=5000,
                state="visible"
            )
            
            if not modal_content:
                logger.error("Could not find modal content")
                return False
            
            # Scroll the modal content to make all filters visible
            await modal_content.evaluate('''
                element => {
                    element.scrollTop = element.scrollHeight;
                    // Additional scroll to ensure we reach the bottom
                    setTimeout(() => {
                        element.scrollTop = element.scrollHeight;
                    }, 100);
                }
            ''')
            await asyncio.sleep(1)  # Wait for scroll to complete
            
            # Apply job type filters if provided
            if job_types:
                for job_type in job_types:
                    # Map job type to the corresponding value
                    job_type_map = {
                        "Full-time": "F",
                        "Part-time": "P",
                        "Contract": "C",
                        "Temporary": "T",
                        "Internship": "I"
                    }
                    
                    job_type_value = job_type.value if hasattr(job_type, 'value') else job_type
                    if job_type_value in job_type_map:
                        value = job_type_map[job_type_value]
                        label_selector = f'label[for="advanced-filter-jobType-{value}"]'
                        
                        # Find and click the label
                        label = await self.page.wait_for_selector(label_selector, timeout=2000)
                        if label:
                            # Scroll the label into view within the modal
                            await label.scroll_into_view_if_needed()
                            await asyncio.sleep(0.5)
                            
                            # Check if the associated checkbox is already checked
                            checkbox = await self.page.query_selector(f'#advanced-filter-jobType-{value}')
                            if checkbox:
                                is_checked = await checkbox.is_checked()
                                if not is_checked:
                                    await label.click()
                                    await asyncio.sleep(0.5)
                                    logger.info(f"Applied job type filter: {job_type_value}")
            
            # Apply remote type filters if provided
            if remote_types:
                for remote_type in remote_types:
                    # Map remote type to the corresponding value
                    remote_type_map = {
                        "Hybrid": "3",
                        "On-site": "1",
                        "Remote": "2"
                    }
                    
                    remote_type_value = remote_type.value if hasattr(remote_type, 'value') else remote_type
                    if remote_type_value in remote_type_map:
                        value = remote_type_map[remote_type_value]
                        label_selector = f'label[for="advanced-filter-workplaceType-{value}"]'
                        
                        # Find and click the label
                        label = await self.page.wait_for_selector(label_selector, timeout=2000)
                        if label:
                            # Scroll the label into view within the modal
                            await label.scroll_into_view_if_needed()
                            await asyncio.sleep(0.5)
                            
                            # Check if the associated checkbox is already checked
                            checkbox = await self.page.query_selector(f'#advanced-filter-workplaceType-{value}')
                            if checkbox:
                                is_checked = await checkbox.is_checked()
                                if not is_checked:
                                    await label.click()
                                    await asyncio.sleep(0.5)
                                    logger.info(f"Applied remote type filter: {remote_type_value}")
            
            # Click the "Show results" button
            show_results_button = await self.page.wait_for_selector(
                'button[data-test-reusables-filters-modal-show-results-button="true"]',
                timeout=2000,
                state="visible"
            )
            
            if show_results_button:
                await show_results_button.click()
                await asyncio.sleep(2)  # Wait for results to update
                logger.info("Applied filters and showing results")
                return True
            else:
                logger.error("Could not find 'Show results' button")
                return False
                
        except Exception as e:
            logger.error(f"Error applying filters: {str(e)}")
            return False

    async def search_jobs(self, keywords: str, location: Optional[str] = None, max_pages: int = 10, 
                         job_types: Optional[List[str]] = None, remote_types: Optional[List[str]] = None,
                         time_period: Optional[TimePeriod] = None, max_jobs: Optional[int] = None) -> List[JobListing]:
        """Search for jobs on LinkedIn using the provided keywords and location.
        
        Args:
            keywords: Search keywords
            location: Optional location to filter by
            max_pages: Maximum number of pages to scrape (default: 2)
            job_types: Optional list of job types to filter by
            remote_types: Optional list of remote types to filter by
            time_period: Optional TimePeriod enum to filter jobs by
            max_jobs: Optional maximum number of jobs to scrape (default: None, meaning no limit)
        """
        if not self.page:
            raise RuntimeError("Browser not initialized")
            
        all_jobs = []
        current_page = 1
        
        try:
            # Initial search with time period filter
            time_period_seconds = time_period.seconds if time_period else None
            await self._navigate_to_jobs_page(time_period_seconds)
            await self._fill_search_inputs(keywords, location)
            await self._click_search_button()
            
            # Apply filters if provided
            if job_types or remote_types:
                logger.info(f"Applying filters - Job types: {job_types}, Remote types: {remote_types}")
                filter_success = await self._apply_filters(job_types, remote_types)
                if not filter_success:
                    logger.warning("Failed to apply filters, continuing with unfiltered results")
                
            # Check for no results banner after applying filters
            await asyncio.sleep(2)  # Wait for results to update
            no_results_banner = await self.page.query_selector('.jobs-search-no-results-banner__image')
            if no_results_banner:
                logger.info("No jobs found matching the search criteria")
                return []
            
            while current_page <= max_pages:
                logger.info(f"Processing page {current_page} of {max_pages}")
                
                # Wait for and get job cards on current page
                remaining_jobs = max_jobs - len(all_jobs) if max_jobs is not None else None
                job_cards = await self._wait_for_job_search_results(remaining_jobs)
                
                # Process jobs on current page
                for card in job_cards:
                    # Check if we've reached the maximum number of jobs
                    if max_jobs is not None and len(all_jobs) >= max_jobs:
                        logger.info(f"Reached maximum number of jobs ({max_jobs})")
                        return all_jobs
                        
                    job_details = await self._extract_job_details(card)
                    if job_details:
                        all_jobs.append(job_details)
                        logger.info(f"Processed job: {job_details.title} at {job_details.company}")
                
                # Try to go to next page
                if current_page < max_pages:
                    has_next_page = await self._click_next_page()
                    if not has_next_page:
                        logger.info("No more pages available")
                        break
                
                current_page += 1
                
            logger.info(f"Total jobs found across {current_page} pages: {len(all_jobs)}")
            return all_jobs
            
        except Exception as e:
            logger.error(f"Error during job search: {str(e)}")
            return all_jobs
            
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
