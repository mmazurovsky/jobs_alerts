"""
LinkedIn job scraper implementation using Playwright.
"""
import asyncio
import logging
import os
import random
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, ElementHandle

from src.core.config import config
from src.data.data import JobListing, StreamManager, TimePeriod, StreamType, StreamEvent

# --- Custom logging formatter to include scraper name between logger name and level ---
class ScraperNameFormatter(logging.Formatter):
    def format(self, record):
        scraper_name = getattr(record, 'scraper_name', None)
        if scraper_name:
            record.name = f"{record.name} [{scraper_name}]"
        return super().format(record)

# Set the formatter for this module's logger
handler = logging.StreamHandler()
handler.setFormatter(ScraperNameFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logger.addHandler(handler)
logger.propagate = False

class LinkedInScraper:
    """LinkedIn job scraper using Playwright."""
    
    def __init__(self, stream_manager: StreamManager, name: Optional[str] = None):
        """Initialize the scraper."""
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.state_file = Path("linkedin_state.json")
        self.stream_manager = stream_manager
        self.name = name
        self.logger = logging.LoggerAdapter(
            logging.getLogger(__name__),
            {"scraper_name": self.name or "unnamed"}
        )

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
                headless=True,  # Run browser in headless mode
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--disable-gpu",
                    "--window-size=1920,1080",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-site-isolation-trials",
                    "--disable-font-subpixel-positioning",
                    "--disable-remote-fonts",
                    "--disable-google-fonts",
                    "--disable-font-antialiasing",
                    "--font-render-hinting=none"
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
                "permissions": ["geolocation"],
                "bypass_csp": True
            }
            
            # Try to load existing state if available
            if self.state_file.exists():
                self.logger.info("Found existing LinkedIn state - loading...")
                self.context = await self.browser.new_context(**context_options)
                with open(self.state_file, "r") as f:
                    await self.context.add_cookies(eval(f.read()))
            else:
                self.context = await self.browser.new_context(**context_options)
            
            # Create new page
            self.page = await self.context.new_page()
            self.page.set_default_timeout(30000)  # 30 seconds timeout
            self.page.set_default_navigation_timeout(30000)  # 30 seconds for navigation
            
            # Monitor responses for 403/429
            self.page.on("response", self._handle_response_status)

            self.logger.info("Browser and page initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize browser: {str(e)}")
            return False

    async def _random_human_delay(self, min_sec=1, max_sec=5):
        delay = random.uniform(min_sec, max_sec)
        self.logger.info(f"Sleeping for {delay:.2f} seconds to simulate human behavior.")
        await asyncio.sleep(delay)

    def _handle_response_status(self, response):
        if response.status in [403, 429]:
            
            self.logger.error(f"Received status {response.status} for {response.url}. Possible throttling or ban.")
            self.post_log_to_stream_manager(f"Received status {response.status} for {response.url}. Possible throttling or ban.")

    async def _simulate_human_actions(self):
        # Random mouse movement and scrolling
        try:
            for _ in range(random.randint(1, 3)):
                x = random.randint(100, 1200)
                y = random.randint(100, 800)
                await self.page.mouse.move(x, y, steps=random.randint(5, 20))
                await asyncio.sleep(random.uniform(0.2, 1.0))
            # Random scroll
            scroll_y = random.randint(100, 1000)
            await self.page.evaluate(f"window.scrollBy(0, {scroll_y})")
            await asyncio.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            self.logger.warning(f"Human simulation failed: {e}")

    async def login(self) -> bool:
        """Login to LinkedIn using Playwright, with robust logging."""
        try:
            if not self.page:
                self.logger.error("Browser not initialized")
                return False

            self.logger.info("Attempting LinkedIn login...")
            await self.page.goto("https://www.linkedin.com/login")
            await self._random_human_delay()

            if ("feed" in self.page.url):
                self.logger.info("Already logged in to LinkedIn")
                return True

            # Check if we're on the "Welcome back" page
            welcome_heading = await self.page.query_selector('h1.header__content__heading')
            if welcome_heading:
                heading_text = await welcome_heading.inner_text()
                self.logger.info(f"Found welcome heading: '{heading_text}'")
                if "Welcome Back" in heading_text:
                    self.logger.info("Detected 'Welcome back' login page")
                    profile_button = await self.page.query_selector('button.member-profile__details')
                    if profile_button:
                        self.logger.info("Found member profile button, clicking...")
                        await profile_button.click()
                        await asyncio.sleep(5)
                    else:
                        self.logger.error("Could not find member profile button on 'Welcome back' page")
                        raise Exception("Could not find member profile button on 'Welcome back' page")
                else:
                    self.logger.info("Heading found but does not indicate 'Welcome back'. Proceeding with regular login flow.")
                    # Regular login page
                    self.logger.info("On regular login page, filling credentials...")
                    username_input = await self.page.query_selector("#username")
                    password_input = await self.page.query_selector("#password")
                    submit_button = await self.page.query_selector("button[type='submit']")
                    self.logger.info(f"username_input found: {username_input is not None}, password_input found: {password_input is not None}, submit_button found: {submit_button is not None}")
                    if not username_input:
                        self.logger.error("Username input field not found on login page.")
                        raise Exception("Username input field not found on login page.")
                    if not password_input:
                        self.logger.error("Password input field not found on login page.")
                        raise Exception("Password input field not found on login page.")
                    if not submit_button:
                        self.logger.error("Submit button not found on login page.")
                        raise Exception("Submit button not found on login page.")
                    self.logger.info("Filling username and password fields...")
                    await username_input.fill(config.linkedin_email)
                    await password_input.fill(config.linkedin_password)
                    self.logger.info("Clicking submit button...")
                    await submit_button.click()
                    self.logger.info("Waiting for login to complete...")
                    await self._random_human_delay(5, 10)
            else:
                self.logger.info("No welcome heading found. Proceeding with regular login flow.")
                # Regular login page
                self.logger.info("On regular login page, filling credentials...")
                username_input = await self.page.query_selector("#username")
                password_input = await self.page.query_selector("#password")
                submit_button = await self.page.query_selector("button[type='submit']")
                self.logger.info(f"username_input found: {username_input is not None}, password_input found: {password_input is not None}, submit_button found: {submit_button is not None}")
                if not username_input:
                    self.logger.error("Username input field not found on login page.")
                    raise Exception("Username input field not found on login page.")
                if not password_input:
                    self.logger.error("Password input field not found on login page.")
                    raise Exception("Password input field not found on login page.")
                if not submit_button:
                    self.logger.error("Submit button not found on login page.")
                    raise Exception("Submit button not found on login page.")
                self.logger.info("Filling username and password fields...")
                await username_input.fill(config.linkedin_email)
                await password_input.fill(config.linkedin_password)
                self.logger.info("Clicking submit button...")
                await submit_button.click()
                self.logger.info("Waiting for login to complete...")
                await self._random_human_delay(5, 10)

            # Check if we're on the feed page or any other LinkedIn page
            if "linkedin.com" in self.page.url and "login" not in self.page.url:
                self.logger.info("Successfully logged in to LinkedIn")
                if self.context:
                    with open(self.state_file, "w") as f:
                        f.write(str(await self.context.cookies()))
                    self.logger.info("Saved LinkedIn session state")
                return True
            else:
                current_url = self.page.url if self.page else None
                if current_url and "linkedin.com/login" in current_url:
                    self.logger.error(f"Login failed - still on login page after submission: {current_url}")
                    await self._handle_login_failure_screenshot(
                        f"Login failed - still on login page after submission: {current_url}",
                        url=current_url,
                        post_to_stream_manager=True
                    )
                else:
                    self.logger.error(f"Login failed - redirected to unexpected URL: {current_url}")
                    await self._handle_login_failure_screenshot(
                        f"Login failed - redirected to unexpected URL: {current_url}",
                        url=current_url,
                        post_to_stream_manager=True
                    )

        except Exception as e:
            self.logger.error(f"Login failed: {str(e)}")
            current_url = self.page.url if self.page else None
            await self._handle_login_failure_screenshot(f"Login failed: {str(e)}", url=current_url, post_to_stream_manager=True)
        return False

    async def _handle_login_failure_screenshot(self, message: str, url: str = None, post_to_stream_manager: bool = False):
        try:
            screenshots_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'screenshots')
            os.makedirs(screenshots_dir, exist_ok=True)
            from datetime import datetime
            screenshot_path = os.path.join(screenshots_dir, f'login_failed_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
            if self.page:
                await self.page.screenshot(path=screenshot_path)
                self.logger.error(f"{message} Screenshot saved to {screenshot_path}")
                if post_to_stream_manager:
                    msg = message
                    if url:
                        msg += f" (URL: {url})"
                    await self.post_log_to_stream_manager(message=msg + f" Screenshot saved to {screenshot_path}", image_path=screenshot_path)
            else:
                self.logger.error(f"{message} (No page available for screenshot)")
                if post_to_stream_manager:
                    msg = message
                    if url:
                        msg += f" (URL: {url})"
                    await self.post_log_to_stream_manager(message=msg + " (No page available for screenshot)")
        except Exception as ss_e:
            self.logger.error(f"Failed to save login failure screenshot: {ss_e}")
            if post_to_stream_manager:
                await self.post_log_to_stream_manager(message=f"Failed to save login failure screenshot: {ss_e}")

    async def _navigate_to_jobs_page(self, time_period_seconds: Optional[int] = None):
        """Navigate to LinkedIn jobs search page.
        
        Args:
            time_period_seconds: Optional time period in seconds to filter jobs by
        """
        self.logger.info("Navigating to LinkedIn jobs search page...")
        base_url = "https://www.linkedin.com/jobs/search/"
        
        # Add time period filter to URL if provided
        if time_period_seconds:
            base_url += f"?f_TPR=r{time_period_seconds}"
            
        await self.page.goto(base_url)
        await self._random_human_delay()

    async def _fill_search_inputs(self, keywords: str, location: Optional[str] = None):
        """Fill in the search inputs with keywords and location."""
        self.logger.info(f"Searching for jobs with keywords: {keywords}")
        search_selectors = [
            'input[aria-label="Search by title, skill, or company"]',
            'input[aria-label="Search job titles or companies"]',
            '#jobs-search-box-keyword-id-ember'
        ]
        
        search_input = None
        for selector in search_selectors:
            try:
                search_input = await self.page.wait_for_selector(selector, timeout=5000)
                if search_input:
                    self.logger.info(f"Found search input using selector: {selector}")
                    break
            except:
                continue

        if not search_input:
            raise Exception("Could not find search input field")
        
        await search_input.click()  # Ensure input is focused
        await search_input.fill("")  # Clear existing text
        await search_input.fill(keywords)
        await asyncio.sleep(0.5)

        # Check if the search input was filled correctly
        input_value = await search_input.input_value()
        if not input_value:
            self.logger.error("Search input field was not filled correctly.")
            raise Exception("Search input field was not filled correctly.")

        if location:
            await self._fill_location_input(location)

    async def _fill_location_input(self, location: str):
        """Fill in the location input field."""
        self.logger.info(f"Adding location filter: {location}")
        location_selectors = [
            'input[aria-label="City, state, or zip code"]',
            'input[aria-label="Location"]',
            '#jobs-search-box-location-id-ember'
        ]
        
        location_input = None
        for selector in location_selectors:
            try:
                location_input = await self.page.wait_for_selector(selector, timeout=5000)
                if location_input:
                    self.logger.info(f"Found location input using selector: {selector}")
                    break
            except:
                continue

        if not location_input:
            raise Exception("Could not find location input field")
        
        await location_input.click()  # Ensure input is focused
        await location_input.fill("")  # Clear existing text
        await location_input.fill(location)
        await asyncio.sleep(0.5)

    async def _click_search_button(self):
        """Click the search button or submit with Enter key."""
        self.logger.info("Looking for search button...")
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
                    self.logger.info(f"Found search button using selector: {selector}")
                    break
            except:
                continue

        if not search_button:
            # If no button found, try pressing Enter in the search input
            self.logger.info("No search button found, trying to submit with Enter key")
            await self.page.keyboard.press("Enter")
        else:
            self.logger.info("Clicking search button...")
            await search_button.click()
        
        # Wait for navigation and network idle
        try:
            await self.page.wait_for_load_state("networkidle", timeout=5000)
            self.logger.info("Page reached network idle state")
        except Exception as e:
            self.logger.warning(f"Timeout waiting for network idle: {str(e)}")
        
        await asyncio.sleep(1.5)  # Wait for search to initiate

    async def _wait_for_job_search_results(self, max_jobs: Optional[int] = None) -> List[ElementHandle]:
        """Wait for job search results to load and scroll to load all jobs.
        
        Args:
            max_jobs: Optional maximum number of jobs to load. If provided, will stop scrolling once this many jobs are found.
        
        Returns:
            List of job card elements
        """
        self.logger.info("Waiting for job search results to load...")
        
        # Wait for the job cards container - use the exact selector for the left side scrollable area
        container_selector = "#main > div > div.scaffold-layout__list-detail-inner.scaffold-layout__list-detail-inner--grow > div.scaffold-layout__list > div"
        
        try:
            job_cards_container = await self.page.wait_for_selector(
                container_selector,
                timeout=5000,
                state="visible"
            )
            if job_cards_container:
                self.logger.info("Found job cards container")
            else:
                self.logger.warning("Could not find job cards container")
                return []
        except Exception as e:
            self.logger.warning(f"Error finding job cards container: {e}")
            return []

        # Wait for initial job cards to load
        await asyncio.sleep(1)
        
        job_cards = []
        seen_job_ids = set()  # Track seen job IDs
        scroll_attempts = 0
        max_scroll_attempts = 10
        last_card_count = 0
        no_new_cards_count = 0
        
        while scroll_attempts < max_scroll_attempts:
            await self._simulate_human_actions()
            # Get current job cards
            current_cards = await self.page.query_selector_all("div.job-card-container")
            self.logger.info(f"Found {len(current_cards)} job cards in current view")
            
            # Update job cards list with new unique cards
            new_cards_found = False
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
                        new_cards_found = True
                        self.logger.info(f"Added new unique job card with ID: {job_id}")
                except Exception as e:
                    self.logger.warning(f"Error extracting job ID from card: {e}")
                    continue
                    
            self.logger.info(f"Total unique job cards found: {len(job_cards)}")
            
            # Check if we have enough jobs
            if max_jobs is not None and len(job_cards) >= max_jobs:
                self.logger.info(f"Found {len(job_cards)} jobs, stopping scroll")
                break
                
            # Check if we found any new cards
            if not new_cards_found:
                no_new_cards_count += 1
                if no_new_cards_count >= 3:  # If no new cards found after 3 attempts, stop scrolling
                    self.logger.info("No new cards found after multiple attempts, stopping scroll")
                    break
            else:
                no_new_cards_count = 0
            
            # Optimized scrolling approach for the left side container
            try:
                # Focus the container first
                await job_cards_container.focus()
                await asyncio.sleep(0.5)
                
                # Proactive scrolling with smaller increments
                await self.page.evaluate('''
                    () => {
                        const container = document.querySelector('#main > div > div.scaffold-layout__list-detail-inner.scaffold-layout__list-detail-inner--grow > div.scaffold-layout__list > div');
                        if (container) {
                            // Get the current scroll position and container height
                            const currentScroll = container.scrollTop;
                            const containerHeight = container.clientHeight;
                            
                            // Calculate a smaller scroll increment (about 2-3 cards worth)
                            const scrollIncrement = Math.min(containerHeight, 800);
                            
                            // Scroll by the increment
                            container.scrollBy({
                                top: scrollIncrement,
                                behavior: 'auto'
                            });
                            
                            // Log scroll position for debugging
                            console.log('Scrolled from', currentScroll, 'to', container.scrollTop);
                        }
                    }
                ''')
                
                # Wait for potential new content to load
                await asyncio.sleep(1.5)
                
            except Exception as e:
                self.logger.warning(f"Error during scrolling: {e}")
                # Try a simple fallback
                try:
                    await self.page.keyboard.press('Space')
                    await asyncio.sleep(1)
                except Exception as e2:
                    self.logger.warning(f"Fallback scroll also failed: {e2}")
            
            scroll_attempts += 1
            self.logger.info(f"Scroll attempt {scroll_attempts}/{max_scroll_attempts}")
            await self._random_human_delay(2, 5)
                
        self.logger.info(f"Final count: Found {len(job_cards)} unique job cards after scrolling")
        return job_cards[:max_jobs] if max_jobs is not None else job_cards

    async def _extract_job_details(self, card) -> Optional[JobListing]:
        """Extract details from a single job card."""
        try:
            # Extract job details directly from the card
            title_elem = await card.query_selector('a[href*="/jobs/view/"]')
            if not title_elem:
                self.logger.warning("Could not find job title link")
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
            self.logger.info(f"Clicking job link: {title}")
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
                # Remove duplicates after splitting and stripping
                job_type_parts = [t.strip() for t in job_type.split('\n') if t.strip()]
                seen = set()
                unique_job_type_parts = []
                for part in job_type_parts:
                    normalized = part.replace('.', '').replace(' ', '').lower()
                    if normalized not in seen:
                        seen.add(normalized)
                        unique_job_type_parts.append(part)
                job_type = ' • '.join(unique_job_type_parts)

            # Get the job link from the job title element
            try:
                # Find the job title link in the card
                title_link = await card.query_selector('a.job-card-list__title--link')
                if not title_link:
                    self.logger.error("Could not find job title link")
                    return None
                
                # Get the href attribute which contains the job ID
                href = await title_link.get_attribute('href')
                if not href:
                    self.logger.error("Could not find href attribute in job title link")
                    return None
                
                # Extract job ID from the href
                if '/jobs/view/' in href:
                    job_id = href.split('/jobs/view/')[1].split('/')[0].split('?')[0]
                    self.logger.info(f"Extracted job ID: {job_id}")
                    # Construct the full job URL
                    job_url = f"https://www.linkedin.com/jobs/view/{job_id}"
                    self.logger.info(f"Constructed job URL: {job_url}")
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
                    self.logger.error(f"Invalid job link format in href: {href}")
                    return None
                
            except Exception as e:
                self.logger.error(f"Error getting job link: {str(e)}")
                return None

        except Exception as e:
            self.logger.error(f"Error processing job card: {str(e)}")
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
                    self.logger.info("Next page button is disabled - reached last page")
                    return False
                
                # Click the next button
                await next_button.click()
                await asyncio.sleep(2)  # Wait for page load
            return True
                
        except Exception as e:
            self.logger.info(f"No next page button found or error: {str(e)}")
            return False

    async def _apply_filters(self, job_types=None, remote_types=None):
        """Apply job type and remote type filters to the search results."""
        try:
            # Click the "All filters" button to open the filter panel
            all_filters_button = await self.page.wait_for_selector(
                'button[aria-label="Show all filters. Clicking this button displays all available filter options."]',
                timeout=10000,
                state="visible"
            )
            
            if not all_filters_button:
                self.logger.error("Could not find 'All filters' button")
                return False
                
            await all_filters_button.click()
            await asyncio.sleep(1.5)  # Wait for filter panel to open
            
            # Find the modal content first
            modal_content = await self.page.wait_for_selector('.artdeco-modal__content', timeout=10000, state="visible")

            # Scroll the modal content to the bottom to ensure all filters are loaded
            await modal_content.evaluate('el => { el.scrollTop = el.scrollHeight; }')
            await asyncio.sleep(0.5)

            # Map human-readable labels to LinkedIn filter codes
            job_type_map = {
                "Full-time": "F",
                "Part-time": "P",
                "Contract": "C",
                "Temporary": "T",
                "Internship": "I",
            }
            remote_type_map = {
                "On-site": "1",
                "Remote": "2",
                "Hybrid": "3",
            }

            # For job types
            if job_types:
                for job_type in job_types:
                    # Accept both JobType class and string
                    jt_label = job_type.label if hasattr(job_type, 'label') else str(job_type)
                    code = job_type_map.get(jt_label)
                    if not code:
                        self.logger.warning(f"No code mapping for job type: {jt_label}")
                        continue
                    label_selector = f'label[for="advanced-filter-jobType-{code}"]'
                    label = await modal_content.wait_for_selector(label_selector, timeout=10000)
                    if label:
                        await label.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        checkbox = await modal_content.query_selector(f'input#advanced-filter-jobType-{code}')
                        if checkbox:
                            is_checked = await checkbox.is_checked()
                            if not is_checked:
                                await label.click()
                                await asyncio.sleep(0.5)
                                self.logger.info(f"Clicked label for job type filter: {jt_label}")
                    else:
                        self.logger.error(f"Could not find label for job type: {jt_label}")
                    await asyncio.sleep(0.5)

            # For remote types
            if remote_types:
                for remote_type in remote_types:
                    rt_label = remote_type.label if hasattr(remote_type, 'label') else str(remote_type)
                    code = remote_type_map.get(rt_label)
                    if not code:
                        self.logger.warning(f"No code mapping for remote type: {rt_label}")
                        continue
                    label_selector = f'label[for="advanced-filter-workplaceType-{code}"]'
                    label = await modal_content.wait_for_selector(label_selector, timeout=10000)
                    if label:
                        await label.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        checkbox = await modal_content.query_selector(f'input#advanced-filter-workplaceType-{code}')
                        if checkbox:
                            is_checked = await checkbox.is_checked()
                            if not is_checked:
                                await label.click()
                                await asyncio.sleep(0.5)
                                self.logger.info(f"Clicked label for remote type filter: {rt_label}")
                    else:
                        self.logger.error(f"Could not find label for remote type: {rt_label}")
                    await asyncio.sleep(0.5)

            # Click the "Show results" button
            show_results_button = await self.page.wait_for_selector(
                'button[data-test-reusables-filters-modal-show-results-button="true"]',
                timeout=10000,
                state="visible"
            )
            if show_results_button:
                await show_results_button.click()
                await asyncio.sleep(2)  # Wait for results to update
                self.logger.info("Applied filters and showing results")
                return True
            else:
                self.logger.error("Could not find 'Show results' button")
                return False
        except Exception as e:
            self.logger.error(f"Error applying filters: {str(e)}")
            return False

    async def search_jobs(self, keywords: str, location: Optional[str] = None, max_pages: int = 10, 
                         job_types: Optional[List[str]] = None, remote_types: Optional[List[str]] = None,
                         time_period: Optional[TimePeriod] = None, max_jobs: Optional[int] = None,
                         blacklist: Optional[List[str]] = None) -> List[JobListing]:
        """Search for jobs on LinkedIn using the provided keywords and location.
        
        Args:
            keywords: Search keywords
            location: Optional location to filter by
            max_pages: Maximum number of pages to scrape (default: 2)
            job_types: Optional list of job types to filter by
            remote_types: Optional list of remote types to filter by
            time_period: Optional TimePeriod enum to filter jobs by
            max_jobs: Optional maximum number of jobs to scrape (default: None, meaning no limit)
            blacklist: Optional list of strings to filter out from job titles
        """
        if not self.page:
            raise RuntimeError("Browser not initialized")
            
        all_jobs = []
        current_page = 1
        
        try:
            # First ensure we're logged in
            self.logger.info("Verifying LinkedIn login status...")
            await self.page.goto("https://www.linkedin.com/feed/", timeout=30000)
            await asyncio.sleep(1)
            
            # Check if we're on the login page or if feed content is missing
            login_form = await self.page.query_selector('#username')
            feed_content = await self.page.query_selector('.feed-shared-update-v2')
            
            if login_form or not feed_content:
                self.logger.info("Not logged in or session invalid - attempting to login...")
                login_success = await self.login()
                if not login_success:
                    raise Exception("Failed to login to LinkedIn")
                await asyncio.sleep(1)
                
                # Verify login was successful
                await self.page.goto("https://www.linkedin.com/feed/", timeout=30000)
                await asyncio.sleep(1)
                feed_content = await self.page.query_selector('.feed-shared-update-v2')
                if not feed_content:
                    # Save screenshot for debugging
                    screenshots_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'screenshots')
                    os.makedirs(screenshots_dir, exist_ok=True)
                    from datetime import datetime
                    screenshot_path = os.path.join(screenshots_dir, f'login_failed_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
                    await self.page.screenshot(path=screenshot_path)
                    self.logger.error(f"Login verification failed - could not find feed content. Screenshot saved to {screenshot_path}")
                    raise Exception("Login verification failed - could not find feed content")
            
            # Now proceed with job search
            time_period_seconds = time_period.seconds if time_period else None
            await self._navigate_to_jobs_page(time_period_seconds)
            await self._fill_search_inputs(keywords, location)
            await self._click_search_button()
            
            # Apply filters if provided
            if job_types or remote_types:
                self.logger.info(f"Applying filters - Job types: {job_types}, Remote types: {remote_types}")
                filter_success = await self._apply_filters(job_types, remote_types)
                if not filter_success:
                    self.logger.warning("Failed to apply filters, continuing with unfiltered results")
                
            # Check for no results banner after applying filters
            await asyncio.sleep(1)  # Wait for results to update
            no_results_banner = await self.page.query_selector('.jobs-search-no-results-banner__image')
            if no_results_banner:
                self.logger.info("No jobs found matching the search criteria")
                return []
            
            while current_page <= max_pages:
                self.logger.info(f"Processing page {current_page}")
                
                # Wait for and get job cards on current page
                remaining_jobs = max_jobs - len(all_jobs) if max_jobs is not None else None
                job_cards = await self._wait_for_job_search_results(remaining_jobs)
                
                # Process jobs on current page
                for card in job_cards:
                    # Check if we've reached the maximum number of jobs
                    if max_jobs is not None and len(all_jobs) >= max_jobs:
                        self.logger.info(f"Reached maximum number of jobs ({max_jobs})")
                        return all_jobs
                        
                    job_details = await self._extract_job_details(card)
                    if job_details:
                        # Blacklist filter
                        if blacklist and any(b.lower() in job_details.title.lower() for b in blacklist):
                            self.logger.info(f"Filtered out job '{job_details.title}' due to blacklist match.")
                            continue
                        # Keyword filter: must be in title or description
                        keyword_lower = keywords.lower()
                        if keyword_lower not in job_details.title.lower() and keyword_lower not in job_details.description.lower():
                            self.logger.info(f"Filtered out job '{job_details.title}' because keyword '{keywords}' not in title or description.")
                            continue
                        # Job type and remote type filter
                        job_type_str = job_details.job_type.lower() if job_details.job_type else ""
                        job_type_match = False
                        remote_type_match = False
                        if job_types:
                            for jt in job_types:
                                jt_str = jt.value.lower() if hasattr(jt, 'value') else str(jt).lower()
                                if jt_str in job_type_str:
                                    job_type_match = True
                                    break
                        else:
                            job_type_match = True  # No filter if not provided
                        if remote_types:
                            for rt in remote_types:
                                rt_str = rt.value.lower() if hasattr(rt, 'value') else str(rt).lower()
                                if rt_str in job_type_str:
                                    remote_type_match = True
                                    break
                        else:
                            remote_type_match = True  # No filter if not provided
                        if not (job_type_match and remote_type_match):
                            self.logger.info(f"Filtered out job '{job_details.title}' because job_type '{job_details.job_type}' does not match job_types or remote_types filter.")
                            continue
                        all_jobs.append(job_details)
                        self.logger.info(f"Processed job: {job_details.title} at {job_details.company}")
                
                # Try to go to next page
                if current_page < max_pages:
                    has_next_page = await self._click_next_page()
                    if not has_next_page:
                        self.logger.info("No more pages available")
                        break
                
                current_page += 1
                
            self.logger.info(f"Total jobs found across {current_page} pages: {len(all_jobs)}")
            return all_jobs
            
        except Exception as e:
            self.logger.error(f"Error during job search: {str(e)}")
            return all_jobs

    async def create_new_session(self):
        """Create a new browser session for a job search."""
        await self.initialize()
        return self

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

    async def post_log_to_stream_manager(self, *, message: str, image_path: Optional[str] = None):
        if not self.stream_manager:
            raise ValueError("stream_manager is not set on LinkedInScraper")
        event_data = {
            "message": message,
            "image_path": image_path
        }
        event = StreamEvent(
            type=StreamType.SEND_LOG,
            data=event_data,
            source="linkedin_scraper"
        )
        self.stream_manager.publish(event)

