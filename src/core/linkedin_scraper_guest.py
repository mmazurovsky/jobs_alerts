import asyncio
import logging
import os
from pathlib import Path
from typing import List, Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from src.data.data import JobType, RemoteType, TimePeriod, ShortJobListing

class LinkedInScraperGuest:
    """LinkedIn job scraper for public/guest access (no login)."""
    def __init__(self, name: Optional[str] = None):
        self.logger = logging.getLogger(f"src.core.linkedin_scraper_guest{f'.{name}' if name else ''}")
        self.name = name or "guest"
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None

    async def _initialize(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        self.logger.info("Initialized Playwright browser for guest scraping.")

    async def close(self):
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.logger.info("Closed Playwright browser for guest scraping.")

    async def search_jobs(
        self,
        keywords: str,
        location: str,
        job_types: Optional[List[JobType]] = None,
        remote_types: Optional[List[RemoteType]] = None,
        time_period: Optional[TimePeriod] = None,
        max_results: int = 25,
    ) -> List[ShortJobListing]:
        """Search jobs on LinkedIn public jobs page as a guest."""
        await self._initialize()
        try:
            # Build URL
            base_url = "https://www.linkedin.com/jobs/search"
            params = [
                f"keywords={keywords.replace(' ', '%20')}",
                f"location={location.replace(' ', '%20')}"
            ]
            if time_period:
                params.append(f"f_TPR={self._get_time_period_code(time_period)}")
            url = f"{base_url}?{'&'.join(params)}"
            self.logger.info(f"Navigating to {url}")
            await self.page.goto(url, timeout=60000)
            await asyncio.sleep(2)

            # Select job type filter if needed
            if job_types:
                await self._apply_job_type_filter(job_types)
            # Select remote type filter if needed
            if remote_types:
                await self._apply_remote_type_filter(remote_types)

            # Wait for jobs to load
            await self._wait_for_selector_with_modal_retry(".jobs-search-results__list-item", timeout=20000)
            job_cards = await self.page.query_selector_all(".jobs-search-results__list-item")
            results = []
            for card in job_cards[:max_results]:
                job = await self._extract_job_details(card)
                if job:
                    results.append(job)
            return results
        finally:
            await self.close()

    async def _apply_job_type_filter(self, job_types: List[JobType]):
        # Click the Job type filter button
        btn = await self.page.query_selector(
            '#jserp-filters > ul > li:nth-child(3) > div > div > button')
        if btn:
            await btn.click()
            await asyncio.sleep(1)
            for jt in job_types:
                label = jt.label
                # Find the label for this job type
                label_el = await self.page.query_selector(f'label:has-text("{label}")')
                if label_el:
                    # Get the for attribute to find the checkbox
                    for_attr = await label_el.get_attribute('for')
                    if for_attr:
                        cb = await self.page.query_selector(f'#{for_attr}')
                        if cb:
                            checked = await cb.is_checked()
                            if not checked:
                                await cb.check()
            # Click outside to close dropdown
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(1)

    async def _apply_remote_type_filter(self, remote_types: List[RemoteType]):
        # Click the Remote filter button
        btn = await self.page.query_selector(
            '#jserp-filters > ul > li:nth-child(6) > div > div > button')
        if btn:
            await btn.click()
            await asyncio.sleep(1)
            for rt in remote_types:
                label = rt.label
                label_el = await self.page.query_selector(f'label:has-text("{label}")')
                if label_el:
                    for_attr = await label_el.get_attribute('for')
                    if for_attr:
                        cb = await self.page.query_selector(f'#{for_attr}')
                        if cb:
                            checked = await cb.is_checked()
                            if not checked:
                                await cb.check()
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(1)

    async def _extract_job_details(self, card) -> Optional[ShortJobListing]:
        # Extract job details from a job card element
        try:
            title = await card.query_selector_eval('a.job-card-list__title', 'el => el.innerText')
            company = await card.query_selector_eval('a.job-card-container__company-name', 'el => el.innerText')
            location = await card.query_selector_eval('span.job-card-container__metadata-item', 'el => el.innerText')
            job_url = await card.query_selector_eval('a.job-card-list__title', 'el => el.href')
            # Extract posted time
            created_ago = ""
            time_elem = await card.query_selector('time.job-search-card__listdate--new, time.job-search-card__listdate')
            if time_elem:
                created_ago = await time_elem.inner_text()
            return ShortJobListing(
                title=title.strip() if title else '',
                company=company.strip() if company else '',
                location=location.strip() if location else '',
                url=job_url.strip() if job_url else '',
                created_ago=created_ago,
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

    async def _wait_for_selector_with_modal_retry(self, selector: str, timeout: int = 20000) -> None:
        """Wait for a selector, and if timeout, close sign-in modal and retry once."""
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
        except Exception as e:
            self.logger.warning(f"Timeout waiting for {selector}: {e}. Checking for sign-in modal...")
            close_btn = await self.page.query_selector('button[aria-label="Dismiss"]')
            if not close_btn:
                close_btn = await self.page.query_selector('button.contextual-sign-in-modal__modal-dismiss')
                if close_btn:
                    self.logger.info("Found sign-in modal close button by class selector.")
            if close_btn:
                await close_btn.click()
                self.logger.info("Closed sign-in modal. Retrying wait for selector.")
                await self.page.wait_for_selector(selector, timeout=timeout)
            else:
                self.logger.error("No sign-in modal found after timeout.") 