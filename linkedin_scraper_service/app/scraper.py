import asyncio
import logging
import os
from pathlib import Path
from typing import List, Optional, Dict
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from shared.data import JobType, RemoteType, TimePeriod, ShortJobListing, StreamEvent, StreamType, FullJobListing
import time
import random
from urllib.parse import urlparse, urlunparse, quote_plus, urlencode
from playwright_stealth import stealth_async
from datetime import datetime, timezone, timedelta
import traceback
from collections import deque
from linkedin_scraper_service.app.llm.litellm_client import LiteLLMClient
from linkedin_scraper_service.app.utils.parallel_executor import execute_parallel_with_semaphore

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
    
    def __init__(self, name: Optional[str] = None, proxy_config: Optional[Dict[str, str]] = None):
        # Logger will be set dynamically in search_jobs
        self.logger = logging.getLogger(f"linkedin_scraper_guest{f'.{name}' if name else ''}")
        self.name = name or "guest"
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._last_log_time = time.time()
        self._watchdog_task = None
        self.proxy_config = proxy_config or self._get_default_proxy_config()
        self._recent_logs = deque(maxlen=50)
        self.llm_client = LiteLLMClient()
        
        class LastLogTimeHandler(logging.Handler):
            def __init__(inner_self, parent):
                super().__init__()
                inner_self.parent = parent
            def emit(inner_self, record):
                inner_self.parent._last_log_time = time.time()
        self.logger.addHandler(LastLogTimeHandler(self))

    async def _watchdog(self):
        self.logger.info("Watchdog started.")
        try:
            while True:
                await asyncio.sleep(5)
                elapsed = time.time() - self._last_log_time
                if elapsed > 300:
                    self.logger.warning(f"No log messages for {elapsed:.1f} seconds. Attempting to close sign-in modal.")
                    try:
                        await self._close_sign_in_modal()
                    except Exception as e:
                        msg = f"Watchdog failed to close modal: {e}"
                        self.logger.error(msg)
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
        """Get shared browser instance with thread safety."""
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
            self.logger.info("Starting new browser context initialization...")
            # Always get the shared browser instance
            self.browser = await self._get_browser()
            # Context options with proxy and human-like settings
            chrome_version = self._get_random_chrome_version()
            context_options = {
                'user_agent': random.choice(self.USER_AGENTS),
                'viewport': random.choice(self.VIEWPORT_SIZES),
                'locale': 'en-US',
                'timezone_id': 'Europe/London',
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
    async def create_new_session(cls, *args, proxy_config=None, **kwargs):
        """Create a new browser context session for a job search."""
        instance = cls(*args, proxy_config=proxy_config, **kwargs)
        await instance._initialize()
        return instance

    async def search_jobs(
        self,
        keywords: str,
        location: Optional[str] = None,
        job_types: Optional[List[JobType]] = None,
        remote_types: Optional[List[RemoteType]] = None,
        time_period: Optional[TimePeriod] = None,
        user_id: Optional[str] = None,
        filter_text: Optional[str] = None,
    ) -> List[FullJobListing]:
        # Set logger name dynamically for this search
        context = []
        if keywords:
            context.append(str(keywords))
        if location:
            context.append(str(location))
        if user_id:
            context.append(str(user_id))
        context_str = ".".join(context)
        logger_name = f"linkedin_scraper_guest{f'.{context_str}' if context_str else ''}"
        self.logger = logging.getLogger(logger_name)
        try:
            # Set a timeout for the entire search operation (5 minutes)
            return await self._search_jobs_internal(
                    keywords, location, job_types, 
                    remote_types, time_period, filter_text
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
            # Always cleanup resources after job search
            await self.close()

    async def _restart_session(self):
        await self._cleanup()
        await self._initialize()

    async def _safe_get_page_info(self) -> str:
        """Safely get page information for debugging without raising exceptions."""
        if not self.page:
            return "No page object available"
        
        try:
            page_url = self.page.url
            page_html = await self.page.content()
            return f"Page URL: {page_url}\nHTML (first 1000 chars): {page_html[:1000]}\nHTML (last 1000 chars): {page_html[-1000:] if len(page_html) > 1000 else page_html}"
        except Exception as e:
            return f"Could not retrieve page info (page may be unstable): {e}"

    async def _get_job_details(self, job_id: str, page: Optional[Page] = None) -> Optional[ShortJobListing]:
        """Get detailed job information by job ID with retry logic on timeout."""
        # Use provided page or create a new one for this request
        current_page = page or await self.context.new_page()
        max_retries = 2
        
        try:
            await stealth_async(current_page)
            
            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        # Switch to different proxy config for retry
                        self.logger.info(f"Retry attempt {attempt} for job_id={job_id}, switching proxy config")
                        old_proxy = self.proxy_config
                        self.proxy_config = self._get_default_proxy_config()
                        if self.proxy_config != old_proxy:
                            self.logger.info(f"Switched proxy from {old_proxy} to {self.proxy_config}")
                            # Restart session with new proxy
                            await self._cleanup()
                            await self._initialize()
                            # Create new page after proxy change
                            if not page:  # Only if we created the page ourselves
                                await current_page.close()
                                current_page = await self.context.new_page()
                                await stealth_async(current_page)
                    
                    api_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
                    public_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
                    
                    await current_page.goto(api_url, timeout=30000, wait_until='domcontentloaded')
                    await self._random_delay(1, 2)  # Reduced delay for parallel processing
                    
                    # Extract job details with updated selectors
                    title_el = await current_page.query_selector('body > section > div > div.top-card-layout__entity-info-container.flex.flex-wrap.papabear\\:flex-nowrap > div > a > h2')
                    title = await title_el.inner_text() if title_el else ''
                    
                    company_el = await current_page.query_selector('body > section > div > div.top-card-layout__entity-info-container.flex.flex-wrap.papabear\\:flex-nowrap > div > h4 > div:nth-child(1) > span:nth-child(1) > a')
                    company = await company_el.inner_text() if company_el else ''
                    
                    location_el = await current_page.query_selector('body > section > div > div.top-card-layout__entity-info-container.flex.flex-wrap.papabear\\:flex-nowrap > div > h4 > div:nth-child(1) > span.topcard__flavor.topcard__flavor--bullet')
                    location = await location_el.inner_text() if location_el else ''
                    
                    created_ago_el = await current_page.query_selector('body > section > div > div.top-card-layout__entity-info-container.flex.flex-wrap.papabear\\:flex-nowrap > div > h4 > div:nth-child(2) > span')
                    created_ago = await created_ago_el.inner_text() if created_ago_el else ''
                    
                    # Extract additional fields for logging (not saved to ShortJobListing)
                    description_el = await current_page.query_selector('[class*=description] > section > div')
                    description_text = await description_el.inner_text() if description_el else ''
                    
                    criteria_el = await current_page.query_selector('[class*=_job-criteria-list]')
                    criteria_text = await criteria_el.inner_text() if criteria_el else ''
                    
                    # Build combined description (criteria + description)
                    description_parts = []
                    if criteria_text:
                        # Convert criteria to single line format
                        criteria_formatted = criteria_text.replace('\n', ', ').strip()
                        description_parts.append(criteria_formatted)
                    if description_text:
                        description_parts.append(description_text)
                    
                    combined_description = '\n'.join(description_parts)
                    
                    # Validate that essential fields are not empty
                    if not title.strip() or not company.strip() or not created_ago.strip():
                        self.logger.warning(f"Job {api_url} has empty essential fields: title='{title}', company='{company}', created_ago='{created_ago}'")
                        # Get page info for debugging but continue trying
                        page_html = await current_page.content()
                        self.logger.error(f"Page content (first 1000 chars): {page_html[:1000]}")
                        break
                    
                    # Log success with URL verification
                    current_url = current_page.url
                    self.logger.info(f"Successfully extracted job details for job_id={job_id} from URL={current_url}")
                    self.logger.info(f"  -> title='{title}', company='{company}', location='{location}', created_ago='{created_ago}'")
                    self.logger.info(f"  -> public_url={public_url}")
                    
                    return ShortJobListing(
                        title=title.strip(),
                        company=company.strip(),
                        location=location.strip(),
                        link=public_url,
                        created_ago=created_ago.strip(),
                        description=combined_description
                    )
                    
                except Exception as e:
                    current_url = current_page.url if current_page else api_url
                    
                    self.logger.error(f"Error getting job details for job_id={job_id} from URL={current_url} (attempt {attempt + 1}): {e}")
                    
                    # Try to get page info for debugging
                    try:
                        page_html = await current_page.content()
                        self.logger.error(f"Error page content (first 500 chars): {page_html[:500]}")
                    except:
                        self.logger.error("Could not retrieve page content for debugging")
                    
                    # If this was the last attempt, return None
                    if attempt == max_retries:
                        self.logger.error(f"Failed to get job details for job_id={job_id} after {max_retries + 1} attempts")
                        return None
        
        finally:
            # Clean up the page if we created it
            if not page and current_page:
                try:
                    await current_page.close()
                except:
                    pass
        
        return None

    async def _get_job_details_bulk(self, job_ids: list[str]) -> list[ShortJobListing]:
        """
        Fetch job details for multiple job IDs in parallel by cycling through different 
        proxy configurations with the same scraper instance.
        """
        async def process_single_job_details(job_id: str, task_index: int) -> tuple[str, Optional[ShortJobListing]]:
            try:
                # Rotate proxy config for this task
                if task_index % 5 == 0:  # Every 5th task gets a new proxy
                    new_proxy_config = self._get_default_proxy_config()
                    await self._update_proxy_config(new_proxy_config)
                    await asyncio.sleep(1)  # Brief delay after proxy change
                
                # Create a dedicated page for this job to avoid interference
                job_page = await self.context.new_page()
                await stealth_async(job_page)
                
                try:
                    # Process the job with dedicated page - return tuple with job_id to maintain mapping
                    job = await self._get_job_details(job_id, page=job_page)
                    if job:
                        self.logger.info(f"Task {task_index}: Job details for job_id={job_id} found")
                        return (job_id, job)
                    else:
                        self.logger.warning(f"Task {task_index}: Job details for job_id={job_id} not found")
                        return (job_id, None)
                finally:
                    # Always close the dedicated page
                    try:
                        await job_page.close()
                    except Exception as e:
                        self.logger.error(f"Error closing page for task {task_index}, job_id={job_id}: {e}")
                        
            except Exception as e:
                self.logger.error(f"Task {task_index}: Error processing job_id={job_id}: {e}")
                return (job_id, None)
        
        # Use the parallel execution utility
        results = await execute_parallel_with_semaphore(
            items=job_ids,
            async_func=process_single_job_details,
            max_concurrent=3,
            operation_name="job details fetching",
            logger=self.logger
        )
        
        # Process results and maintain job_id mapping
        successful_jobs = []
        job_results_dict = {}
        
        for result in results:
            if isinstance(result, tuple) and len(result) == 2:
                job_id, job_data = result
                job_results_dict[job_id] = job_data
                if job_data is not None:
                    successful_jobs.append(job_data)
        
        # Log the mapping for verification
        self.logger.info(f"Job ID to result mapping verification:")
        for job_id in job_ids[:5]:  # Log first 5 for verification
            result_status = "SUCCESS" if job_results_dict.get(job_id) else "FAILED/MISSING"
            self.logger.info(f"  job_id={job_id} -> {result_status}")
        
        return successful_jobs

    async def _update_proxy_config(self, new_proxy_config: Optional[Dict[str, str]] = None):
        """Update proxy configuration and restart browser context without full reinitialization."""
        try:
            old_proxy = self.proxy_config
            self.proxy_config = new_proxy_config or self._get_default_proxy_config()
            
            if self.proxy_config != old_proxy:
                self.logger.info(f"Updating proxy config from {old_proxy} to {self.proxy_config}")
                
                # Cleanup current context but keep browser
                if hasattr(self, 'page') and self.page:
                    await self.page.close()
                if hasattr(self, 'context') and self.context:
                    await self.context.close()
                
                # Create new context with updated proxy
                chrome_version = self._get_random_chrome_version()
                context_options = {
                    'user_agent': random.choice(self.USER_AGENTS),
                    'viewport': random.choice(self.VIEWPORT_SIZES),
                    'locale': 'en-US',
                    'timezone_id': 'Europe/London',
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
                
                # Add new proxy config
                if self.proxy_config:
                    context_options['proxy'] = self.proxy_config
                    self.logger.info(f"Applied new proxy: {self.proxy_config.get('server', 'configured')}")
                else:
                    self.logger.info("Using direct connection (no proxy)")
                
                # Create new context with updated proxy
                self.context = await self.browser.new_context(**context_options)
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
                
                # Create new page
                self.page = await self.context.new_page()
                await stealth_async(self.page)
                await self._block_resource_types()
                
                self.logger.info("Successfully updated proxy configuration and reinitialized context")
            else:
                self.logger.info("Proxy configuration unchanged, no update needed")
                
        except Exception as e:
            self.logger.error(f"Failed to update proxy configuration: {e}")
            raise

    async def _search_jobs_internal(
        self,
        keywords: str,
        location: Optional[str] = None,
        job_types: Optional[List[JobType]] = None,
        remote_types: Optional[List[RemoteType]] = None,
        time_period: Optional[TimePeriod] = None,
        filter_text: Optional[str] = None,
    ) -> List[FullJobListing]:
        """Search for jobs using LinkedIn API endpoint with pagination."""
        self._watchdog_task = asyncio.create_task(self._watchdog())
        self.logger.info(f"Starting job search for keywords='{keywords}', location='{location}'")
        
        # Build base URL with query parameters
        base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        params = {
            "keywords": keywords,
        }
        
        # Add location if provided
        if location:
            params["location"] = location
        
        # Add job type filters (f_JT)
        if job_types:
            jt_mapping = {
                "Full-time": "F",
                "Part-time": "P", 
                "Contract": "C",
                "Temporary": "T",
                "Volunteer": "V",
                "Internship": "I",
                "Other": "O"
            }
            jt_values = [jt_mapping.get(jt.label, "") for jt in job_types if jt.label in jt_mapping]
            if jt_values:
                params["f_JT"] = ",".join(jt_values)
                
        # Add remote type filters (f_WT)
        if remote_types:
            wt_mapping = {
                "On-site": "1",
                "Remote": "2", 
                "Hybrid": "3"
            }
            wt_values = [wt_mapping.get(rt.label, "") for rt in remote_types if rt.label in wt_mapping]
            if wt_values:
                params["f_WT"] = ",".join(wt_values)
                
        # Add time period filter (f_TPR)
        if time_period:
            params["f_TPR"] = time_period.linkedin_code
            
        all_job_ids = set()
        max_pages_to_scrape = time_period.get_max_pages_to_scrape()
        
        for iteration in range(max_pages_to_scrape):
            start_pos = iteration * 10
            params["start"] = start_pos
            
            # Build URL with current pagination
            search_url = f"{base_url}?{urlencode(params)}"
            
            self.logger.info(f"Fetching jobs page {iteration + 1} (start={start_pos}): {search_url}")
            
            try:
                # Navigate to the API endpoint
                await self.page.goto(search_url, timeout=20000)
                await self._random_delay(2, 4)
                
                # Check for empty HTML response that indicates end of results
                body_element = await self.page.query_selector('body')
                if body_element:
                    body_text = await body_element.inner_text()
                    body_html = await body_element.inner_html()
                    # Check if body is effectively empty (no text content and minimal HTML)
                    if (not body_text.strip() and 
                        (not body_html.strip() or len(body_html.strip()) < 50)):
                        self.logger.info(f"Empty body content detected on page {iteration + 1}, stopping pagination")
                        break
                
                # Check for no results section
                no_results_section = await self.page.query_selector('section.core-section-container.my-3.no-results')
                if no_results_section:
                    self.logger.info(f"No results section detected on page {iteration + 1}")
                    break
                    
                # Extract job cards using new selectors
                job_cards = await self.page.query_selector_all('li > div.base-card')
                self.logger.info(f"Found {len(job_cards)} job cards on page {iteration + 1}")
                
                if len(job_cards) == 0:
                    self.logger.info(f"No job cards found on page {iteration + 1}, stopping pagination")
                    break
                    
                # Extract job IDs from the cards
                page_job_ids = set()
                for card in job_cards:
                    try:
                        # Look for data-entity-urn attribute
                        entity_urn = await card.get_attribute('data-entity-urn')
                        if entity_urn and entity_urn.startswith('urn:li:jobPosting:'):
                            job_id = entity_urn.split(':')[-1]
                            page_job_ids.add(job_id)
                            all_job_ids.add(job_id)
                    except Exception as e:
                        self.logger.error(f"Failed to extract job ID from card: {e}")
                continue
                        
                self.logger.info(f"Extracted {len(page_job_ids)} job IDs from page {iteration + 1}")
                
                # If we found fewer than 10 jobs, this is likely the last page
                if len(job_cards) < 10:
                    self.logger.info(f"Found only {len(job_cards)} jobs on page {iteration + 1}, stopping pagination")
                    break
                    
            except Exception as e:
                self.logger.error(f"Error fetching page {iteration + 1}: {e}")
                break
            
        self.logger.info(f"Total unique job IDs collected: {len(all_job_ids)}")
        
        if not all_job_ids:
            self.logger.info("No job IDs found, returning empty list")
            return []
            
        # Get job details for all collected IDs
        results = await self._get_job_details_with_llm_filtering(
            list(all_job_ids), keywords, job_types, remote_types, location, filter_text
        )
        self.logger.info(f"Successfully extracted {len(results)} job details from {len(all_job_ids)} job IDs")
        
        return results

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
            found_labels = await self.page.query_selector_all('div[aria-label="Job type filter options"] label')
            label_texts = [await label_el.inner_text() for label_el in found_labels]
            self.logger.info(f"Job type filter labels found: {label_texts}")
            self.logger.info(f"Job types to apply: {job_types}")
            any_applied = False
            for applied_job_type in job_types:
                applied_label_text = applied_job_type.label.lower()
                for label_el in found_labels:
                    found_text = (await label_el.inner_text()).lower()
                    if applied_label_text in found_text:
                        is_visible = await label_el.is_visible()
                        is_enabled = await label_el.is_enabled()
                        self.logger.info(f"Label '{found_text}' is_visible={is_visible}, is_enabled={is_enabled}")
                        if is_visible and is_enabled:
                            await self._human_like_click(label_el)
                            self.logger.info(f"Clicked label for job type: {applied_job_type.label}")
                            await self._random_delay(0.3, 0.8)
                            for_attr = await label_el.get_attribute('for')
                            if for_attr:
                                cb = await self.page.query_selector(f'#{for_attr}')
                                if cb:
                                    await cb.check()
                                    checked = await cb.is_checked()
                                    self.logger.info(f"Checkbox for job type '{applied_job_type.label}' checked: {checked}")
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
            self.logger.info(f"Remote types to apply: {remote_types}")
            any_applied = False
            for rt in remote_types:
                label_text = rt.label.lower()
                for label_el in labels:
                    text = (await label_el.inner_text()).lower()
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
                    self.logger.error(f"Proxy connection test failed on attempt {attempt}: {e}")
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

    async def _wait_for_results_list_with_retries(self, context: str, max_retries: int = 3, min_sleep: float = 2.0, max_sleep: float = 8.0, timeout: int = 15000) -> bool:
        """
        Wait for the .jobs-search__results-list container with retries and random sleep.
        Also checks for the no-results section.
        Returns True if results list found, False if no-results section found or not found after retries.
        """
        no_results_selector = 'section.core-section-container.my-3.no-results'
        for attempt in range(1, max_retries + 1):
            try:
                self.logger.info(f"[{context}] Attempt {attempt}: Waiting for .jobs-search__results-list...")
                await self._random_delay(min_sleep, max_sleep)
                # Check for no-results section first
                no_results_section = await self.page.query_selector(no_results_selector)
                if no_results_section:
                    self.logger.info(f"[{context}] No results section detected: '{no_results_selector}' (returning immediately)")
                    return False  # Return immediately, do not retry
                await self.page.wait_for_selector('.jobs-search__results-list', timeout=timeout)
                self.logger.info(f"[{context}] .jobs-search__results-list found.")
                return True
            except Exception as e:
                self.logger.error(f"[{context}] Attempt {attempt}: .jobs-search__results-list not found: {e}")
        url = self.page.url if self.page else None
        self.logger.error(f"[{context}] .jobs-search__results-list not found after {max_retries} attempts. Current URL: {url}")
        try:
            html = await self.page.content()
            self.logger.error(f"[{context}] Page HTML (first 2000 chars): {html[:2000]}")
        except Exception as html_error:
            self.logger.error(f"[{context}] Failed to get page HTML or URL: {html_error}")
        return False 

    async def _get_job_details_with_llm_filtering(
        self,
        job_ids: List[str],
        keywords: str,
        job_types: Optional[List[JobType]] = None,
        remote_types: Optional[List[RemoteType]] = None,
        location: Optional[str] = None,
        filter_text: Optional[str] = None
    ) -> List[FullJobListing]:
        """
        Fetch job details and process them through LLM for filtering and scoring.
        Returns FullJobListing objects with techstack and compatibility scores.
        """
        # First get all job details
        jobs = await self._get_job_details_bulk(job_ids)
        if not jobs:
            return []
        
        # Log the number of jobs
        self.logger.info(f"Number of jobs before LLM processing: {len(jobs)}")
        
        # Process through LLM - the client now returns FullJobListing objects directly
        try:
            filtered_jobs = await self.llm_client.enrich_jobs(
                jobs=jobs,
                keywords=keywords,
                job_types=job_types,
                remote_types=remote_types,
                location=location,
                filter_text=filter_text
            )

            filtered_jobs = [job for job in filtered_jobs if job.compatibility_score is not None and job.compatibility_score > 30]
            
            self.logger.info(f"LLM processing completed: {len(filtered_jobs)} jobs filtered and sorted from {len(filtered_jobs)} total")
            return filtered_jobs
            
        except Exception as e:
            self.logger.error(f"LLM processing failed: {e}")
            # Fallback: create FullJobListing without LLM enhancement
            fallback_jobs = [
                FullJobListing(
                    title=job.title,
                    company=job.company,
                    location=job.location,
                    link=job.link,
                    created_ago=job.created_ago,
                    techstack=[],
                    compatibility_score=0
                )
                for job in jobs
            ]
            
            return fallback_jobs 