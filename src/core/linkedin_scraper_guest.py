import asyncio
import logging
import os
from pathlib import Path
from typing import List, Optional, Dict
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from src.data.data import JobType, RemoteType, TimePeriod, ShortJobListing, StreamEvent, StreamType
import time
import random
from urllib.parse import urlparse, urlunparse

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
    
    def __init__(self, name: Optional[str] = None, stream_manager=None, proxy_config: Optional[Dict[str, str]] = None):
        self.logger = logging.getLogger(f"src.core.linkedin_scraper_guest{f'.{name}' if name else ''}")
        self.name = name or "guest"
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self._last_log_time = time.time()
        self._watchdog_task = None
        self._patch_logger()
        self.stream_manager = stream_manager
        self.proxy_config = proxy_config or self._get_default_proxy_config()

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

    async def _initialize(self):
        try:
            self.logger.info("Starting browser initialization...")
            self.playwright = await async_playwright().start()
            
            # Browser launch options
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
            
            self.logger.info("Launching browser...")
            self.browser = await self.playwright.chromium.launch(**launch_options)
            self.logger.info("Browser launched successfully")
            
            # Context options with proxy and human-like settings
            chrome_version = self._get_random_chrome_version()
            context_options = {
                'user_agent': random.choice(self.USER_AGENTS),
                'viewport': random.choice(self.VIEWPORT_SIZES),
                'locale': 'en-US',
                'timezone_id': 'America/New_York',
                'geolocation': None,  # Can add geolocation if needed
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
            
            try:
                self.logger.info("Creating browser context...")
                self.context = await self.browser.new_context(**context_options)
                self.logger.info("Browser context created successfully")
            except Exception as context_error:
                self.logger.error(f"Failed to create browser context: {context_error}")
                if self.proxy_config:
                    self.logger.error(f"Proxy connection may have failed: {self.proxy_config.get('server', 'configured')}")
                    self.logger.info("Retrying without proxy...")
                    # Remove proxy and try again
                    context_options_no_proxy = context_options.copy()
                    if 'proxy' in context_options_no_proxy:
                        del context_options_no_proxy['proxy']
                    try:
                        self.context = await self.browser.new_context(**context_options_no_proxy)
                        self.logger.info("Browser context created successfully without proxy")
                        self.proxy_config = None  # Disable proxy for this session
                    except Exception as fallback_error:
                        self.logger.error(f"Failed to create browser context even without proxy: {fallback_error}")
                        raise
                else:
                    raise
            
            # Add stealth scripts to avoid detection
            await self.context.add_init_script("""
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Set platform to Linux
                Object.defineProperty(navigator, 'platform', {
                    get: () => 'Linux x86_64'
                });
                
                // Set Chrome-specific properties
                Object.defineProperty(navigator, 'vendor', {
                    get: () => 'Google Inc.'
                });
                
                Object.defineProperty(navigator, 'vendorSub', {
                    get: () => ''
                });
                
                Object.defineProperty(navigator, 'productSub', {
                    get: () => '20030107'
                });
                
                // Mock plugins for Chrome on Linux
                Object.defineProperty(navigator, 'plugins', {
                    get: () => ({
                        length: 3,
                        0: { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                        1: { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                        2: { name: 'Native Client', filename: 'internal-nacl-plugin' }
                    })
                });
                
                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                // Override chrome property with realistic Chrome features
                window.chrome = {
                    runtime: {
                        onConnect: undefined,
                        onMessage: undefined
                    },
                    loadTimes: function() {
                        return {
                            commitLoadTime: Date.now() / 1000 - Math.random() * 10,
                            connectionInfo: 'http/1.1',
                            finishDocumentLoadTime: Date.now() / 1000 - Math.random() * 5,
                            finishLoadTime: Date.now() / 1000 - Math.random() * 3,
                            firstPaintAfterLoadTime: 0,
                            firstPaintTime: Date.now() / 1000 - Math.random() * 8,
                            navigationType: 'Other',
                            npnNegotiatedProtocol: 'unknown',
                            requestTime: Date.now() / 1000 - Math.random() * 15,
                            startLoadTime: Date.now() / 1000 - Math.random() * 12,
                            wasAlternateProtocolAvailable: false,
                            wasFetchedViaSpdy: false,
                            wasNpnNegotiated: false
                        };
                    },
                    csi: function() {
                        return {
                            pageT: Date.now() - Math.random() * 1000,
                            startE: Date.now() - Math.random() * 2000,
                            tran: 15
                        };
                    }
                };
                
                // Override permissions
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({
                        query: (parameters) => (
                            parameters.name === 'notifications' ?
                                Promise.resolve({ state: Notification.permission }) :
                                Promise.resolve({ state: 'granted' })
                        )
                    })
                });
                
                // Mock hardware concurrency for typical Linux system
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 8
                });
                
                // Mock device memory for typical Linux system
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8
                });
                
                // Mock connection for typical broadband
                Object.defineProperty(navigator, 'connection', {
                    get: () => ({
                        effectiveType: '4g',
                        rtt: 50,
                        downlink: 10
                    })
                });
            """)
            
            try:
                self.logger.info("Creating new page...")
                self.page = await self.context.new_page()
                self.logger.info("Page created successfully")
                await self._block_resource_types()
                # Test navigation to verify everything works
                self.logger.info("Testing navigation to about:blank...")
                await self.page.goto('about:blank', timeout=10000)
                self.logger.info(f"Test navigation successful, current URL: {self.page.url}")
                
            except Exception as page_error:
                self.logger.error(f"Failed to create page or test navigation: {page_error}")
                raise
            
            self.logger.info("Initialized Playwright browser for guest scraping with human-like behavior.")
            
        except Exception as e:
            self.logger.error(f"Browser initialization failed: {e}")
            await self._cleanup()
            raise
    
    async def _cleanup(self):
        """Clean up browser resources."""
        try:
            if hasattr(self, 'page') and self.page:
                await self.page.close()
            if hasattr(self, 'context') and self.context:
                await self.context.close()
            if hasattr(self, 'browser') and self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright') and self.playwright:
                await self.playwright.stop()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    async def close(self):
        await self._cleanup()
        self.logger.info("Closed Playwright browser for guest scraping.")

    @classmethod
    async def create_new_session(cls, *args, stream_manager=None, proxy_config=None, **kwargs):
        """Create a new browser session for a job search."""
        instance = cls(*args, stream_manager=stream_manager, proxy_config=proxy_config, **kwargs)
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
            return await asyncio.wait_for(
                self._search_jobs_internal(
                    keywords, location, max_pages, job_types, 
                    remote_types, time_period, max_jobs, blacklist
                ),
                timeout=300  # 5 minutes
            )
        except asyncio.TimeoutError:
            self.logger.error(f"Search for '{keywords}' timed out after 5 minutes")
            return []
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
        for attempt in range(1, max_retries + 1):
            try:
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
                    await self._cleanup()
                    # Reapply the same proxy config
                    await self._initialize()

                self.logger.info(f"Current URL before navigation: {self.page.url}")
                self.logger.info(f"Navigating to {url}")
                await self.page.goto(url, timeout=60000, wait_until='domcontentloaded')
                self.logger.info(f"Successfully navigated to: {self.page.url}")
                if 'chrome-error://chromewebdata/' in self.page.url:
                    raise Exception("Navigation ended up on unexpected URL: chrome-error://chromewebdata/")
                break  # Success!
            except Exception as nav_error:
                self.logger.error(f"Attempt {attempt} navigation failed: {nav_error}")
                if attempt == max_retries:
                    await self._post_watchdog_screenshot(f"All navigation attempts failed for {url}: {nav_error}")
                    return []
                await asyncio.sleep(2 * attempt)  # Exponential backoff
        try:
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

            # Select job type filter if needed
            if job_types:
                self.logger.info(f"Applying job type filters: {[jt.label for jt in job_types]}")
                await self._random_delay(1, 3)
                await self._apply_job_type_filter(job_types)
            # Select remote type filter if needed
            if remote_types:
                self.logger.info(f"Applying remote type filters: {[rt.label for rt in remote_types]}")
                await self._random_delay(1, 3)
                await self._apply_remote_type_filter(remote_types)

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
            no_results_section = await self.page.query_selector('section.no-results')
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

            # Get all job cards after scrolling
            job_cards = await self.page.query_selector_all('.jobs-search__results-list > li')
            self.logger.info(f"Found {len(job_cards)} job cards after scrolling.")
            results = []
            limit = max_jobs if max_jobs is not None else len(job_cards)
            for idx, card in enumerate(job_cards[:limit]):
                job = await self._extract_job_details(card, idx)
                if job:
                    if blacklist and any(b.lower() in job.title.lower() for b in blacklist):
                        self.logger.info(f"Filtered out job '{job.title}' due to blacklist match.")
                        continue
                    results.append(job)
            self.logger.info(f"Extracted {len(results)} jobs from {len(job_cards)} cards.")
            return results
        finally:
            if self._watchdog_task:
                self._watchdog_task.cancel()
                try:
                    await self._watchdog_task
                except asyncio.CancelledError:
                    pass
            await self.close()

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
        # Click the Job type filter button
        btn = await self.page.query_selector(
            '#jserp-filters > ul > li:nth-child(3) > div > div > button')
        if btn:
            await self._human_like_click(btn)
            await self._random_delay(0.5, 1.5)
            # Get all labels in the job type filter dropdown
            labels = await self.page.query_selector_all('div[aria-label="Job type filter options"] label')
            label_texts = [await label_el.inner_text() for label_el in labels]
            self.logger.info(f"Job type filter labels found: {label_texts}")
            for jt in job_types:
                label_text = jt.label.lower()
                found = False
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
                            found = True
                            break
                        else:
                            self.logger.warning(f"Label for job type '{jt.label}' is not visible or not enabled.")
                if not found:
                    self.logger.warning(f"Job type label not found or not clickable in dropdown: {jt.label}")
            # Click the 'Done' button for job type filter
            await self._random_delay(0.5, 1)
            done_btn = await self.page.query_selector('#jserp-filters > ul > li:nth-child(3) > div > div > div > button')
            if done_btn:
                await self._human_like_click(done_btn)
                self.logger.info("Clicked 'Done' button for job type filter.")
            else:
                self.logger.info("No 'Done' button found for job type filter.")
            # Click outside to close dropdown
            await self.page.keyboard.press('Escape')
            await self._random_delay(0.5, 1.5)

    async def _apply_remote_type_filter(self, remote_types: List[RemoteType]):
        # Click the Remote filter button
        btn = await self.page.query_selector(
            '#jserp-filters > ul > li:nth-child(7) > div > div > button')
        if btn:
            await self._human_like_click(btn)
            await self._random_delay(0.5, 1.5)
            # Get all labels in the remote type filter dropdown
            labels = await self.page.query_selector_all('div[aria-label="Remote filter options"] label')
            label_texts = [await label_el.inner_text() for label_el in labels]
            self.logger.info(f"Remote type filter labels found: {label_texts}")
            for rt in remote_types:
                label_text = rt.label.lower()
                found = False
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
                            found = True
                            break
                        else:
                            self.logger.warning(f"Label for remote type '{rt.label}' is not visible or not enabled.")
                if not found:
                    self.logger.warning(f"Remote type label not found or not clickable in dropdown: {rt.label}")
            # Click the 'Done' button for remote type filter
            await self._random_delay(0.5, 1)
            done_btn = await self.page.query_selector('#jserp-filters > ul > li:nth-child(7) > div > div > div > button')
            if done_btn:
                await self._human_like_click(done_btn)
                self.logger.info("Clicked 'Done' button for remote type filter.")
            else:
                self.logger.info("No 'Done' button found for remote type filter.")
            await self.page.keyboard.press('Escape')
            await self._random_delay(0.5, 1.5)

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
                self.logger.info("No 'Reject' cookies button found.")
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

    async def _post_watchdog_screenshot(self, message: str):
        if not self.page or not self.stream_manager:
            return
        try:
            screenshots_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'screenshots')
            os.makedirs(screenshots_dir, exist_ok=True)
            from datetime import datetime
            screenshot_path = os.path.join(screenshots_dir, f'watchdog_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
            await self.page.screenshot(path=screenshot_path)
            event_data = {
                "message": message + f" Screenshot saved to {screenshot_path}",
                "image_path": screenshot_path
            }
            event = StreamEvent(
                type=StreamType.SEND_LOG,
                data=event_data,
                source="linkedin_scraper_guest"
            )
            self.stream_manager.publish(event)
        except Exception as e:
            self.logger.error(f"Failed to post watchdog screenshot: {e}")

    async def check_proxy_connection(self):
        try:
            await self._initialize()
            test_url = "https://www.linkedin.com/"
            self.logger.info(f"Testing proxy connection by navigating to {test_url}")
            await self.page.goto(test_url, timeout=20000)
            self.logger.info("Proxy connection test succeeded.")
            await self.close()
            return True
        except Exception as e:
            self.logger.error(f"Proxy connection test failed: {e}")
            await self._post_watchdog_screenshot(f"Proxy connection test failed: {e}")
            await self.close()
            return False 