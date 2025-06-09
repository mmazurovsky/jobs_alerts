import asyncio
import logging
import os
from pathlib import Path
from typing import List, Optional, Dict
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from shared.data import JobType, RemoteType, TimePeriod, ShortJobListing, StreamEvent, StreamType
import time
import random
from urllib.parse import urlparse, urlunparse
from playwright_stealth import stealth_async
import datetime as datetime
import pytz as pytz
import traceback
from collections import deque

class LinkedInScraperGuest:
    """LinkedIn job scraper for public/guest access (no login)."""
    
    # User agents for rotation - Chrome on Linux only
    USER_AGENTS = [
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
    ]
    
    # Viewport sizes for variety
    VIEWPORT_SIZES = [
        {'width': 1920, 'height': 1080},
        {'width': 1366, 'height': 768},
        {'width': 1536, 'height': 864},
        {'width': 1440, 'height': 900},
        {'width': 1680, 'height': 1050},
    ]
    
    _browser: Optional[Browser] = None
    _playwright = None
    _browser_lock = asyncio.Lock()
    
    def __init__(self, name: Optional[str] = None, proxy_config: Optional[Dict[str, str]] = None, keywords: Optional[str] = None, location: Optional[str] = None):
        # Add keywords and location to logger name for context
        context = []
        if keywords:
            context.append(str(keywords))
        if location:
            context.append(str(location))
        context_str = ".".join(context)
        logger_name = f"linkedin_scraper_guest{f'.{name}' if name else ''}{f'.{context_str}' if context_str else ''}"
        self.logger = logging.getLogger(logger_name)
        self.name = name or "guest"
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._last_log_time = time.time()
        self._watchdog_task = None
        self._patch_logger()
        self.proxy_config = proxy_config or self._get_default_proxy_config()
        self._recent_logs = deque(maxlen=50)
        class MemoryLogHandler(logging.Handler):
            def emit(inner_self, record):
                msg = self.logger.handlers[0].format(record) if self.logger.handlers else record.getMessage()
                self._recent_logs.append(msg)
        self.logger.addHandler(MemoryLogHandler())

    def _patch_logger(self):
        """Patch the logger to update last log time on every log."""
        orig_handle = self.logger.handle
        parent = self
        def handle(record):
            parent._last_log_time = time.time()
            orig_handle(record)
        self.logger.handle = handle

    async def _watchdog(self):
        self.logger.info("Watchdog started.")
        try:
            while True:
                await asyncio.sleep(5)
                elapsed = time.time() - self._last_log_time
                if elapsed > 40:
                    self.logger.warning(f"No log messages for {elapsed:.1f} seconds. Attempting to close sign-in modal.")
                    try:
                        await self._close_sign_in_modal()
                    except Exception as e:
                        msg = f"Watchdog failed to close modal: {e}"
                        self.logger.error(msg)
                        await self._post_watchdog_screenshot(msg)
                    # Reset timer so we don't spam
                    self._last_log_time = time.time()
        except asyncio.CancelledError:
            msg = "Watchdog stopped."
            self.logger.info(msg)

    def _get_default_proxy_config(self) -> Optional[Dict[str, str]]:
        """Get default proxy configuration from environment variables."""
        proxy_server = os.getenv('PROXY_SERVER')
        proxy_username = os.getenv('PROXY_USERNAME')
        proxy_password = os.getenv('PROXY_PASSWORD')
        proxy_ports_str = os.getenv("PROXY_PORTS", "")
        proxy_ports = [int(port.strip()) for port in proxy_ports_str.split(",") if port.strip()]
        
        if proxy_server:
            # Randomly select port from 10001-10010
            random_port = random.choice(proxy_ports)
            
            # Parse the proxy server URL to replace the port
            if '://' in proxy_server:
                protocol, rest = proxy_server.split('://', 1)
                if ':' in rest:
                    host, _ = rest.split(':', 1)
                else:
                    host = rest
                proxy_server_with_port = f"{protocol}://{host}:{random_port}"
            else:
                # If no protocol specified, assume http
                if ':' in proxy_server:
                    host, _ = proxy_server.split(':', 1)
                else:
                    host = proxy_server
                proxy_server_with_port = f"http://{host}:{random_port}"
            
            self.logger.info(f"Using proxy server with random port: {proxy_server_with_port}")
            
            config = {'server': proxy_server_with_port}
            if proxy_username and proxy_password:
                config['username'] = proxy_username
                config['password'] = proxy_password
            return config
        return None

    def _get_random_chrome_version(self) -> str:
        """Get a random Chrome version for headers."""
        versions = ['116', '117', '118', '119', '120', '121']
        return random.choice(versions)

    async def _random_delay(self, min_seconds: float = 1.0, max_seconds: float = 5.0):
        """Add a random delay to simulate human behavior."""
        delay = random.uniform(min_seconds, max_seconds)
        self.logger.debug(f"Random delay: {delay:.2f} seconds")
        await asyncio.sleep(delay)

    async def _human_like_mouse_movement(self):
        """Simulate human-like mouse movement."""
        if not self.page:
            return
        try:
            # Get viewport size
            viewport = self.page.viewport_size
            if viewport:
                # Random mouse movements
                for _ in range(random.randint(1, 3)):
                    x = random.randint(100, viewport['width'] - 100)
                    y = random.randint(100, viewport['height'] - 100)
                    await self.page.mouse.move(x, y)
                    await asyncio.sleep(random.uniform(0.1, 0.3))
        except Exception as e:
            self.logger.debug(f"Mouse movement error: {e}")

    async def _human_like_typing(self, text: str):
        """Type text with human-like speed variations."""
        for char in text:
            await self.page.keyboard.type(char)
            # Variable typing speed
            await asyncio.sleep(random.uniform(0.05, 0.15))

    async def _block_resource_types(self):
        if not self.page:
            return
        async def route_intercept(route, request):
            if request.resource_type in ["image", "media", "font", "stylesheet"]:
                await route.abort()
            elif any(domain in request.url for domain in ["doubleclick.net", "google-analytics.com", "ads.linkedin.com"]):
                await route.abort()
            else:
                await route.continue_()
        await self.page.route("**/*", route_intercept)

    @classmethod
    async def _get_browser(cls, launch_options=None):
        async with cls._browser_lock:
            if cls._browser is None:
                if cls._playwright is None:
                    cls._playwright = await async_playwright().start()
                if launch_options is None:
                    launch_options = {
                        'headless': True,
                        'args': [
                            '--no-sandbox',
                            '--disable-blink-features=AutomationControlled',
                            '--disable-dev-shm-usage',
                            '--disable-extensions',
                            '--disable-plugins',
                            '--disable-default-apps',
                            '--disable-background-timer-throttling',
                            '--disable-backgrounding-occluded-windows',
                            '--disable-renderer-backgrounding',
                            '--disable-features=TranslateUI',
                            '--disable-ipc-flooding-protection',
                            '--no-first-run',
                            '--no-default-browser-check',
                            '--disable-web-security',
                            '--disable-features=VizDisplayCompositor',
                            '--disable-infobars',
                            '--disable-notifications',
                            '--disable-popup-blocking',
                            '--disable-save-password-bubble',
                            '--disable-translate',
                            '--disable-background-networking',
                            '--disable-sync',
                            '--disable-default-apps',
                            '--disable-extensions-file-access-check',
                            '--disable-extensions-http-throttling',
                            '--disable-component-extensions-with-background-pages',
                        ]
                    }
                cls._browser = await cls._playwright.chromium.launch(**launch_options)
            return cls._browser

    async def _initialize(self):
        try:
            self.logger.info("Starting browser/context initialization...")
            # Always get the shared browser instance
            self.browser = await self._get_browser()
            # Context options with proxy and human-like settings
            chrome_version = self._get_random_chrome_version()
            context_options = {
                'user_agent': random.choice(self.USER_AGENTS),
                'viewport': random.choice(self.VIEWPORT_SIZES),
                'locale': 'en-US',
                'timezone_id': 'America/New_York',
                'geolocation': None,
                'permissions': [],
                'extra_http_headers': {
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Sec-Ch-Ua': f'"Not_A Brand";v="8", "Chromium";v="{chrome_version}", "Google Chrome";v="{chrome_version}"',
                    'Sec-Ch-Ua-Mobile': '?0',
                    'Sec-Ch-Ua-Platform': '"Linux"',
                    'Cache-Control': 'max-age=0',
                }
            }
            # Add proxy if configured
            if self.proxy_config:
                context_options['proxy'] = self.proxy_config
                self.logger.info(f"Using proxy: {self.proxy_config.get('server', 'configured')}")
            else:
                self.logger.info("No proxy configured, using direct connection")
            self.context = await self.browser.new_context(**context_options)
            self.logger.info("Created new browser context")
            # Add stealth scripts to avoid detection
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'platform', { get: () => 'Linux x86_64' });
                Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.' });
                Object.defineProperty(navigator, 'vendorSub', { get: () => '' });
                Object.defineProperty(navigator, 'productSub', { get: () => '20030107' });
                Object.defineProperty(navigator, 'plugins', { get: () => ({ length: 3, 0: { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' }, 1: { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' }, 2: { name: 'Native Client', filename: 'internal-nacl-plugin' } }) });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                window.chrome = { runtime: { onConnect: undefined, onMessage: undefined }, loadTimes: function() { return { commitLoadTime: Date.now() / 1000 - Math.random() * 10, connectionInfo: 'http/1.1', finishDocumentLoadTime: Date.now() / 1000 - Math.random() * 5, finishLoadTime: Date.now() / 1000 - Math.random() * 3, firstPaintAfterLoadTime: 0, firstPaintTime: Date.now() / 1000 - Math.random() * 8, navigationType: 'Other', npnNegotiatedProtocol: 'unknown', requestTime: Date.now() / 1000 - Math.random() * 15, startLoadTime: Date.now() / 1000 - Math.random() * 12, wasAlternateProtocolAvailable: false, wasFetchedViaSpdy: false, wasNpnNegotiated: false }; }, csi: function() { return { pageT: Date.now() - Math.random() * 1000, startE: Date.now() - Math.random() * 2000, tran: 15 }; } };
                Object.defineProperty(navigator, 'permissions', { get: () => ({ query: (parameters) => ( parameters.name === 'notifications' ? Promise.resolve({ state: Notification.permission }) : Promise.resolve({ state: 'granted' }) ) }) });
                Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
                Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
                Object.defineProperty(navigator, 'connection', { get: () => ({ effectiveType: '4g', rtt: 50, downlink: 10 }) });
            """)
            self.logger.info("Creating new page...")
            self.page = await self.context.new_page()
            await stealth_async(self.page)
            self.logger.info("Stealth script injected.")
            await self._block_resource_types()
            self.logger.info("Testing navigation to about:blank...")
            await self.page.goto('about:blank', timeout=10000)
            self.logger.info(f"Test navigation successful, current URL: {self.page.url}")
            self.logger.info("Initialized Playwright context for guest scraping with human-like behavior.")
        except Exception as e:
            self.logger.error(f"Context initialization failed: {e}")
            await self._cleanup()
            raise

    async def _cleanup(self):
        """Clean up context and page resources only."""
        self.logger.info("Cleaning up context and page resources...")
        try:
            if hasattr(self, 'page') and self.page:
                await self.page.close()
            if hasattr(self, 'context') and self.context:
                await self.context.close()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    async def close(self):
        await self._cleanup()
        self.logger.info("Closed Playwright context for guest scraping.")

    @classmethod
    async def create_new_session(cls, *args, proxy_config=None, keywords=None, location=None, **kwargs):
        """Create a new browser context session for a job search."""
        instance = cls(*args, proxy_config=proxy_config, keywords=keywords, location=location, **kwargs)
        await instance._initialize()
        return instance

    async def search_jobs(
        self,
        keywords: str,
        location: Optional[str] = None,
        max_pages: int = 2,
        job_types: Optional[List[JobType]] = None,
        remote_types: Optional[List[RemoteType]] = None,
        time_period: Optional[TimePeriod] = None,
        max_jobs: Optional[int] = None,
        blacklist: Optional[List[str]] = None,
    ) -> List[ShortJobListing]:
        """Search for jobs with a timeout to prevent hanging."""
        try:
            # Set a timeout for the entire search operation (5 minutes)
            return await self._search_jobs_internal(
                    keywords, location, max_pages, job_types, 
                    remote_types, time_period, max_jobs, blacklist
            )
        except Exception as e:
            self.logger.error(f"Search for '{keywords}' failed: {e}")
            return []
        finally:
            # Cancel watchdog if it's running
            if hasattr(self, '_watchdog_task') and self._watchdog_task:
                self._watchdog_task.cancel()
                try:
                    await self._watchdog_task
                except asyncio.CancelledError:
                    pass

    async def _restart_session(self):
        await self._cleanup()
        await self._initialize()

    async def _get_job_details(self, job_id: str) -> Optional[ShortJobListing]:
        """Fetch job details for a single job id from the job detail API page."""
        try:
            api_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
            public_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
            await self.page.goto(api_url, timeout=30000, wait_until='domcontentloaded')
            await self._random_delay(0.5, 1.5)
            # Title
            title_el = await self.page.query_selector('body > section > div > div.top-card-layout__entity-info-container.flex.flex-wrap.papabear\\:flex-nowrap > div > a > h2')
            title = await title_el.inner_text() if title_el else ''
            # Company
            company_el = await self.page.query_selector('body > section > div > div.top-card-layout__entity-info-container.flex.flex-wrap.papabear\\:flex-nowrap > div > h4 > div:nth-child(1) > span:nth-child(1) > a')
            company = await company_el.inner_text() if company_el else ''
            # Location
            location_el = await self.page.query_selector('body > section > div > div.top-card-layout__entity-info-container.flex.flex-wrap.papabear\\:flex-nowrap > div > h4 > div:nth-child(1) > span.topcard__flavor.topcard__flavor--bullet')
            location = await location_el.inner_text() if location_el else ''
            # Posted time
            posted_el = await self.page.query_selector('body > section > div > div.top-card-layout__entity-info-container.flex.flex-wrap.papabear\\:flex-nowrap > div > h4 > div:nth-child(2) > span')
            created_ago = await posted_el.inner_text() if posted_el else ''
            return ShortJobListing(
                title=title.strip(),
                company=company.strip(),
                location=location.strip(),
                link=public_url,
                created_ago=created_ago.strip(),
            )
        except Exception as e:
            self.logger.error(f"Failed to get job details for job_id={job_id}: {e}")
            return None

    async def _get_job_details_bulk(self, job_ids: list[str]) -> list[ShortJobListing]:
        """Fetch job details for a list of job ids."""
        results = []
        for job_id in job_ids:
            job = await self._get_job_details(job_id)
            if job:
                results.append(job)
        return results

    async def _search_jobs_internal(
        self,
        keywords: str,
        location: Optional[str] = None,
        max_pages: int = 2,
        job_types: Optional[List[JobType]] = None,
        remote_types: Optional[List[RemoteType]] = None,
        time_period: Optional[TimePeriod] = None,
        max_jobs: Optional[int] = None,
        blacklist: Optional[List[str]] = None,
    ) -> List[ShortJobListing]:
        self._watchdog_task = asyncio.create_task(self._watchdog())
        max_retries = 3
        url = None
        attempt = 1
        while attempt <= max_retries:
            try:
                # Return empty list if CET time is between 00:30 and 06:30
                berlin_tz = pytz.timezone('Europe/Berlin')
                now_berlin = datetime.datetime.now(berlin_tz)
                if (now_berlin.hour == 1 and now_berlin.minute >= 30) or (1 < now_berlin.hour < 6) or (now_berlin.hour == 6 and now_berlin.minute < 30):
                    self.logger.info("Current time in CET is between 00:30 and 06:30. Skipping job search.")
                    return []

                # Build URL
                base_url = "https://www.linkedin.com/jobs/search"
                params = [
                    f"keywords={keywords.replace(' ', '%20')}"
                ]
                if location:
                    params.append(f"location={location.replace(' ', '%20')}")
                if time_period:
                    params.append(f"f_TPR={self._get_time_period_code(time_period)}")
                url = f"{base_url}?{'&'.join(params)}"

                if attempt > 1:
                    await self._restart_session()

                self.logger.info(f"Current URL before navigation: {self.page.url}")
                self.logger.info(f"Navigating to {url}")
                await self.page.goto(url, timeout=60000, wait_until='domcontentloaded')
                self.logger.info(f"Successfully navigated to: {self.page.url}")
                if 'chrome-error://chromewebdata/' in self.page.url:
                    raise Exception("Navigation ended up on unexpected URL: chrome-error://chromewebdata/")

                await self._random_delay(2, 4)
                current_url_after_delay = self.page.url
                self.logger.info(f"URL after delay: {current_url_after_delay}")
                await self._human_like_mouse_movement()
                await self._close_sign_in_modal()
                await self._reject_cookies()

                # Check for no results after loading the page, before applying filters
                self.logger.info("Checking for no-results section before applying filters...")
                no_results_section = await self.page.query_selector('section.no-results')
                if no_results_section:
                    self.logger.info("No jobs found - detected 'no-results' section before filters. Skipping filter application.")
                    return []
                
                # Select remote type filter if needed
                if remote_types:
                    selected_filters = [rt.label for rt in remote_types]
                    self.logger.info(f"Trying to apply remote type filters: {selected_filters}")
                    await self._random_delay(1, 3)
                    remote_type_applied = await self._apply_remote_type_filter(remote_types)
                    if not remote_type_applied:
                        labels = await self.page.query_selector_all('div[aria-label="Remote filter options"] label')
                        label_texts = [await label_el.inner_text() for label_el in labels]
                        current_url = self.page.url
                        self.logger.info(f"None of selected remote type filters could be applied. URL: {current_url}, Available remote type filters: {label_texts}, Selected remote type filters: {selected_filters}")
                        return []
                    
                # Select job type filter if needed
                if job_types:
                    selected_filters = [jt.label for jt in job_types]
                    self.logger.info(f"Trying to apply job type filters: {selected_filters}")
                    await self._random_delay(1, 3)
                    job_type_applied = await self._apply_job_type_filter(job_types)
                    if not job_type_applied:
                        labels = await self.page.query_selector_all('div[aria-label="Job type filter options"] label')
                        label_texts = [await label_el.inner_text() for label_el in labels]
                        current_url = self.page.url
                        self.logger.info(f"None of selected job type filters could be applied. URL: {current_url}, Available job type filters: {label_texts}, Selected job type filters: {selected_filters}")
                        return []

                # Check for authwall in URL after applying filters
                current_url = self.page.url
                if 'authwall' in current_url:
                    self.logger.warning(f"Authwall detected in URL: {current_url}. Waiting before going back to previous page.")
                    await self._random_delay(2, 4)
                    await self.page.go_back()
                    await self._random_delay(1.5, 3)
                    current_url = self.page.url
                    self.logger.info(f"Returned to URL: {current_url}")
                    if 'authwall' in current_url:
                        self.logger.warning(f"Still on authwall after going back. Aborting search.")
                        return []

                # Check for no results again after applying filters
                self.logger.info("Checking for no-results section after applying filters...")
                no_results_section = None
                max_retries = 3
                for attempt_retry in range(1, max_retries + 1):
                    try:
                        await self._random_delay(2, 5)
                        no_results_section = await self.page.query_selector('section.no-results')
                        break
                    except Exception as e:
                        self.logger.error(f"Attempt {attempt_retry}: Error checking for no-results section: {e}")
                        if attempt_retry < max_retries:
                            await asyncio.sleep(1.5 * attempt_retry)
                        else:
                            # Log page state before raising
                            try:
                                current_url = self.page.url
                                html_snippet = await self.page.content()
                                self.logger.error(f"Page state on failure (URL): {current_url}")
                                self.logger.error(f"Page state on failure (HTML snippet): {html_snippet[:2000]}")
                            except Exception as log_e:
                                self.logger.error(f"Failed to log page state: {log_e}")
                            raise
                if no_results_section:
                    self.logger.info("No jobs found after applying filters - detected 'no-results' section")
                    return []

                # Wait for jobs container to load
                self.logger.info("Waiting for .jobs-search__results-list container after filters...")
                try:
                    await self.page.wait_for_selector('.jobs-search__results-list', timeout=60000)
                except Exception as wait_error:
                    self.logger.error(f"Timeout or error waiting for .jobs-search__results-list: {wait_error}")
                    html = await self.page.content()
                    self.logger.error(f"Page HTML (first 2000 chars): {html[:2000]}")
                    await self._post_watchdog_screenshot(f"Timeout or error waiting for .jobs-search__results-list: {wait_error}")
                    return []
                container = await self.page.query_selector('.jobs-search__results-list')
                if container:
                    self.logger.info(".jobs-search__results-list container found.")
                    self.logger.info("Delaying before waiting for job cards...")
                    await self._random_delay(2, 4)
                    await self._scroll_job_results()
                else:
                    self.logger.warning(".jobs-search__results-list container NOT found!")

                # # After scrolling job results, check for sign-in overlay
                # overlay_selector = 'h2.blurred_overlay__title'
                # overlay_el = await self.page.query_selector(overlay_selector)
                # if overlay_el:
                #     overlay_text = await overlay_el.inner_text()
                #     if 'Sign in to view' in overlay_text:
                #         self.logger.error("Detected LinkedIn overlay: 'Sign in to view all job postings'. Aborting search.")
                #         await self._restart_session()
                #         await asyncio.sleep(2 * attempt)
                #         attempt += 1
                #         continue
                # Get all job cards after scrolling
                job_cards = await self.page.query_selector_all('.jobs-search__results-list > li')
                self.logger.info(f"Found {len(job_cards)} job cards after scrolling.")
                # Extract job ids only from data-entity-urn inside the job card div
                job_ids = []
                for card in job_cards:
                    div = await card.query_selector('div[data-entity-urn]')
                    if div:
                        entity_urn = await div.get_attribute('data-entity-urn')
                        if entity_urn and entity_urn.startswith('urn:li:jobPosting:'):
                            job_id = entity_urn.split(':')[-1]
                            job_ids.append(job_id)
                if max_jobs is not None:
                    job_ids = job_ids[:max_jobs]
                self.logger.info(f"Collected {len(job_ids)} job ids for detail extraction.")
                # Get job details for all job ids
                results = await self._get_job_details_bulk(job_ids)
                self.logger.info(f"Extracted {len(results)} jobs from {len(job_ids)} job ids.")
                return results
            except Exception as nav_error:
                if attempt == max_retries:
                    await self._post_watchdog_screenshot(
                        f"All navigation attempts failed for {url}: {nav_error}",
                        include_logs=True
                    )
                    return []
                self.logger.error(f"Navigation error: {nav_error}, restarting session...")
                await self._restart_session()
                await asyncio.sleep(2 * attempt)
                attempt += 1
                continue
        return []

    async def _human_like_click(self, element):
        """Click an element with human-like behavior - random position within element."""
        try:
            # Get element bounding box
            box = await element.bounding_box()
            if box:
                # Calculate random position within element
                x = box['x'] + random.uniform(box['width'] * 0.2, box['width'] * 0.8)
                y = box['y'] + random.uniform(box['height'] * 0.2, box['height'] * 0.8)
                
                # Move mouse to position and click
                await self.page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
                await self.page.mouse.click(x, y)
            else:
                # Fallback to normal click
                await element.click()
        except Exception as e:
            self.logger.debug(f"Human-like click failed, using normal click: {e}")
            await element.click()

    async def _apply_job_type_filter(self, job_types: List[JobType]):
        # Find the Job type filter button by aria-label
        btn = await self.page.query_selector('button[aria-label^="Job type filter"]')
        if btn:
            await self._human_like_click(btn)
            await self._random_delay(0.5, 1.5)
            labels = await self.page.query_selector_all('div[aria-label="Job type filter options"] label')
            label_texts = [await label_el.inner_text() for label_el in labels]
            self.logger.info(f"Job type filter labels found: {label_texts}")
            any_applied = False
            for jt in job_types:
                label_text = jt.label.lower()
                for label_el in labels:
                    text = (await label_el.inner_text()).lower()
                    self.logger.info(f"Checking label: '{text}' for job type '{label_text}'")
                    if label_text in text:
                        is_visible = await label_el.is_visible()
                        is_enabled = await label_el.is_enabled()
                        self.logger.info(f"Label '{text}' is_visible={is_visible}, is_enabled={is_enabled}")
                        if is_visible and is_enabled:
                            await self._human_like_click(label_el)
                            self.logger.info(f"Clicked label for job type: {jt.label}")
                            await self._random_delay(0.3, 0.8)
                            for_attr = await label_el.get_attribute('for')
                            if for_attr:
                                cb = await self.page.query_selector(f'#{for_attr}')
                                if cb:
                                    await cb.check()
                                    checked = await cb.is_checked()
                                    self.logger.info(f"Checkbox for job type '{jt.label}' checked: {checked}")
                            any_applied = True
                            break
            await self._random_delay(0.5, 1)
            done_btn = await self.page.query_selector('#jserp-filters > ul > li:nth-child(3) > div > div > div > button')
            if done_btn:
                await self._human_like_click(done_btn)
                self.logger.info("Clicked 'Done' button for job type filter.")
            else:
                self.logger.info("No 'Done' button found for job type filter.")
            await self.page.keyboard.press('Escape')
            await self._random_delay(0.5, 1.5)
            return any_applied
        return False

    async def _apply_remote_type_filter(self, remote_types: List[RemoteType]):
        # Find the Remote filter button by aria-label
        btn = await self.page.query_selector('button[aria-label^="Remote filter"]')
        if btn:
            await self._human_like_click(btn)
            await self._random_delay(0.5, 1.5)
            labels = await self.page.query_selector_all('div[aria-label="Remote filter options"] label')
            label_texts = [await label_el.inner_text() for label_el in labels]
            self.logger.info(f"Remote type filter labels found: {label_texts}")
            any_applied = False
            for rt in remote_types:
                label_text = rt.label.lower()
                for label_el in labels:
                    text = (await label_el.inner_text()).lower()
                    self.logger.info(f"Checking label: '{text}' for remote type '{label_text}'")
                    if label_text in text:
                        is_visible = await label_el.is_visible()
                        is_enabled = await label_el.is_enabled()
                        self.logger.info(f"Label '{text}' is_visible={is_visible}, is_enabled={is_enabled}")
                        if is_visible and is_enabled:
                            await self._human_like_click(label_el)
                            self.logger.info(f"Clicked label for remote type: {rt.label}")
                            await self._random_delay(0.3, 0.8)
                            for_attr = await label_el.get_attribute('for')
                            if for_attr:
                                cb = await self.page.query_selector(f'#{for_attr}')
                                if cb:
                                    await cb.check()
                                    checked = await cb.is_checked()
                                    self.logger.info(f"Checkbox for remote type '{rt.label}' checked: {checked}")
                            any_applied = True
                            break
            await self._random_delay(0.5, 1)
            done_btn = await self.page.query_selector('#jserp-filters > ul > li:nth-child(7) > div > div > div > button')
            if done_btn:
                await self._human_like_click(done_btn)
                self.logger.info("Clicked 'Done' button for remote type filter.")
            else:
                self.logger.info("No 'Done' button found for remote type filter.")
            await self.page.keyboard.press('Escape')
            await self._random_delay(0.5, 1.5)
            return any_applied
        return False

    @staticmethod
    def _strip_query(url: str) -> str:
        parsed = urlparse(url)
        return urlunparse(parsed._replace(query="", fragment=""))

    async def _extract_job_details(self, card, idx: int = 0) -> Optional[ShortJobListing]:
        # Extract job details from a job card element
        try:
            # For guest cards, structure is different
            title_el = await card.query_selector('a.base-card__full-link')
            title = await title_el.inner_text() if title_el else ''
            job_url = await title_el.get_attribute('href') if title_el else ''
            job_url = self._strip_query(job_url)
            company_el = await card.query_selector('h4.base-search-card__subtitle a, h4.base-search-card__subtitle')
            company = await company_el.inner_text() if company_el else ''
            location_el = await card.query_selector('span.job-search-card__location')
            location = await location_el.inner_text() if location_el else ''
            time_el = await card.query_selector('time')
            created_ago = await time_el.inner_text() if time_el else ''
            self.logger.info(f"Extracted job: title='{title}', company='{company}', location='{location}', url='{job_url}', created_ago='{created_ago}'")
            return ShortJobListing(
                title=title.strip(),
                company=company.strip(),
                location=location.strip(),
                link=job_url.strip(),
                created_ago=created_ago.strip(),
            )
        except Exception as e:
            self.logger.error(f"Failed to extract job details: {e}")
            return None

    def _get_time_period_code(self, time_period: TimePeriod) -> str:
        # Map seconds to LinkedIn's rXXXXXX code
        mapping = {
            300: "r300",         # 5 minutes
            600: "r600",         # 10 minutes
            900: "r900",         # 15 minutes
            1800: "r1800",       # 30 minutes
            3600: "r3600",       # 1 hour
            14400: "r14400",     # 4 hours
            86400: "r86400",     # 24 hours
            604800: "r604800",   # 7 days
        }
        return mapping.get(time_period.seconds, f"r{time_period.seconds}")

    async def _close_sign_in_modal(self):
        """Close the LinkedIn sign-in modal if it appears."""
        # Try the most specific selector first, then fall back to others
        selectors = [
            '#base-contextual-sign-in-modal > div > section > button',
            'button[aria-label="Dismiss"]',
            'button.contextual-sign-in-modal__modal-dismiss',
            'button:has(svg)',  # Generic: any button with an SVG (the X)
        ]
        for selector in selectors:
            try:
                btn = await self.page.query_selector(selector)
                if btn:
                    await self._human_like_click(btn)
                    self.logger.info(f"Closed sign-in modal using selector: {selector}")
                    await self._random_delay(0.5, 1.5)
                    return True
            except Exception as e:
                self.logger.warning(f"Error trying to close modal with {selector}: {e}")
        return False

    async def _reject_cookies(self):
        """Reject cookies if the consent banner is present."""
        try:
            btn = await self.page.query_selector('#artdeco-global-alert-container > div > section > div > div.artdeco-global-alert-action__wrapper > button:nth-child(2)')
            if btn:
                await self._human_like_click(btn)
                self.logger.info("Clicked 'Reject' cookies button.")
                await self._random_delay(0.3, 0.8)
            else:
                self.logger.warning("No 'Reject' cookies button found.")
        except Exception as e:
            self.logger.warning(f"Failed to reject cookies: {e}")

    async def _scroll_job_results(self):
        """Scroll the job results list section to load more jobs using scrollIntoView on the last card."""
        try:
            self.logger.info("Starting scrollIntoView scrolling for job results list...")
            container = await self.page.query_selector('#main-content > section.two-pane-serp-page__results-list')
            if not container:
                container = await self.page.query_selector('.jobs-search__results-list')
            if not container:
                self.logger.warning("No main job results container found, cannot scroll.")
                return
            job_card_selector = '.jobs-search__results-list > li'
            max_scroll_attempts = 10
            seen_jobs = set()  # Store unique job identifiers (title + company)
            
            for i in range(max_scroll_attempts):
                cards = await self.page.query_selector_all(job_card_selector)
                current_jobs = set()
                
                # Extract title and company for each card to create unique identifiers
                for card in cards:
                    try:
                        title_el = await card.query_selector('a.base-card__full-link')
                        title = await title_el.inner_text() if title_el else ''
                        company_el = await card.query_selector('h4.base-search-card__subtitle a, h4.base-search-card__subtitle')
                        company = await company_el.inner_text() if company_el else ''
                        
                        if title and company:
                            job_id = f"{title.strip()}::{company.strip()}"
                            current_jobs.add(job_id)
                    except Exception:
                        continue
                
                new_jobs = current_jobs - seen_jobs
                self.logger.info(f"Scroll {i+1}/{max_scroll_attempts}: {len(cards)} cards found, {len(current_jobs)} unique jobs, {len(new_jobs)} new.")
                
                # If no new jobs were found, stop scrolling
                if len(new_jobs) == 0 and i > 0:  # Allow at least one scroll attempt
                    self.logger.info(f"No new jobs found after scroll attempt {i+1}. Stopping scrolling.")
                    break
                
                # Scroll to the last card if there are cards
                if cards:
                    # Human-like scrolling: sometimes scroll to middle cards too
                    if random.random() < 0.3 and len(cards) > 5:  # 30% chance
                        target_card = cards[len(cards) // 2]  # Middle card
                    else:
                        target_card = cards[-1]  # Last card
                    
                    await target_card.evaluate('el => el.scrollIntoView({behavior: "smooth", block: "center"})')
                    
                    # Variable delay after scroll
                    await self._random_delay(1, 2.5)
                    
                    # Occasionally do small mouse movements while waiting
                    if random.random() < 0.5:  # 50% chance
                        await self._human_like_mouse_movement()
                
                # Update seen jobs
                seen_jobs.update(current_jobs)
            
            self.logger.info(f"Finished scrollIntoView scrolling. Total unique job cards seen: {len(seen_jobs)}")
        except Exception as e:
            self.logger.warning(f"Failed to scroll job results list: {e}")

    async def _post_watchdog_screenshot(self, message: str, include_logs: bool = False):
        if not self.page:
            return
        try:
            screenshots_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'screenshots')
            os.makedirs(screenshots_dir, exist_ok=True)
            from datetime import datetime
            screenshot_path = os.path.join(screenshots_dir, f'watchdog_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
            await self.page.screenshot(path=screenshot_path)
            if include_logs:
                logs = "\n".join(self._recent_logs)
                stack = traceback.format_exc()
                message += f"\n\nRecent logs (last 50):\n{logs}\n\nStack trace:\n{stack}"
            event_data = {
                "message": message + f"\n\nScreenshot saved to {screenshot_path}",
                "image_path": screenshot_path
            }
            event = StreamEvent(
                type=StreamType.SEND_LOG,
                data=event_data,
                source="linkedin_scraper_guest"
            )
            # TODO: add logging of screenshot
        except Exception as e:
            self.logger.error(f"Failed to post watchdog screenshot: {e}")

    async def check_proxy_connection(self):
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                await self._initialize()
                test_url = "https://www.linkedin.com/"
                self.logger.info(f"Testing proxy connection by navigating to {test_url} (attempt {attempt})")
                await self.page.goto(test_url, timeout=20000)
                self.logger.info("Proxy connection test succeeded.")
                await self._cleanup()
                return True
            except Exception as e:
                await self._cleanup()
                if attempt == max_retries:
                    await self._post_watchdog_screenshot(f"Proxy connection test failed on attempt {attempt}: {e}")
                    return False
                await asyncio.sleep(2 * attempt)

    @staticmethod
    def _is_masked(value: str) -> bool:
        # Consider masked if the value contains at least one '*' character
        return value is not None and '*' in value 

    @classmethod
    async def close_all_browsers(cls):
        async with cls._browser_lock:
            if cls._browser is not None:
                await cls._browser.close()
                cls._browser = None
            if cls._playwright is not None:
                await cls._playwright.stop()
                cls._playwright = None 