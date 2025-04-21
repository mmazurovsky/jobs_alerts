"""
LinkedIn job scraper implementation using AgentQL.
"""
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import agentql
from playwright.async_api import async_playwright, Browser, Page

from .config import config

logger = logging.getLogger(__name__)

# LinkedIn login page URL
INITIAL_URL = "https://www.linkedin.com/login?fromSignIn=true&trk=guest_homepage-basic_nav-header-signin"
JOBS_URL = "https://www.linkedin.com/jobs/search"


# AgentQL query for login form - using element IDs
LOGIN_INPUT_QUERY = """
{
    username_input
    password_input
    sign_in_button
}
"""

JOBS_SEARCH_QUERY = """
{
    job_search_title_input(type=input, id contains "jobs-search-box-keyword-id")
    job_search_location_input(type=input, id contains "jobs-search-box-location-id")
    search_button(type=button, class contains "jobs-search-box__submit-button")
}
"""

JOB_LIST_QUERY = """
{
    jobs[] {
        job_title(name of the job title),
        job_company_name(name of the company that is hiring)        j
    }
}
"""

JOB_DETAILS_QUERY = """
{
    job_title
    company_name
    job_type (remote or hybrid or onsite)
    job_location
    job_posted_date
    share_button
}
"""

SHARE_BUTTON_QUERY = """
{
    copy_link_button
}
"""

@dataclass
class JobListing:
    """Data class for job listing information."""
    title: str
    company: str
    location: str
    posted_date: str
    job_url: str


class LinkedInScraper:
    """
    LinkedIn job scraper using AgentQL.
    """
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.agentql_page = None
        self.playwright = None
        
        # Set AgentQL API key from config
        logger.info(f"Setting AgentQL API key: {config.agentql_api_key[:5]}...")  # Only show first 5 chars for security
        os.environ["AGENTQL_API_KEY"] = config.agentql_api_key
        logger.info(f"Environment AGENTQL_API_KEY: {os.getenv('AGENTQL_API_KEY', '')[:5]}...")  # Only show first 5 chars for security

    async def __aenter__(self):
        """Async context manager entry."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def login(self) -> bool:
        """
        Login to LinkedIn using AgentQL.
        
        Returns:
            bool: True if login successful, False otherwise
        """
        if (os.path.exists("linkedin_state.json")):
            logger.info("Found existing LinkedIn state - loading...")
            context = await self.browser.new_context(storage_state="linkedin_state.json")
            self.page = await context.new_page()
            self.agentql_page = await agentql.wrap_async(self.page)
            return True
        else : 
            try:
                self.page = await self.browser.new_page()
                self.agentql_page = await agentql.wrap_async(self.page)
                await self.page.goto(INITIAL_URL)
                
                # Wait for the page to load
                await self.page.wait_for_load_state("networkidle")
                
                # Get the login form elements
                form = await self.agentql_page.query_elements(LOGIN_INPUT_QUERY)
                
                # Fill in the login form
                await form.username_input.fill(config.linkedin_email)
                await self.page.wait_for_timeout(1000)
                await form.password_input.fill(config.linkedin_password)
                await self.page.wait_for_timeout(1000)
                
                # Click the sign in button
                await form.sign_in_button.click()
                
                # Wait for navigation to complete and specifically for the feed URL
                try:
                    # Wait up to 30 seconds for navigation to the feed
                    await self.page.wait_for_url("**/feed/**", timeout=30000)
                    current_url = self.page.url
                    logger.info(f"Successfully navigated to: {current_url}")
                    
                    # Double check we're actually on a feed page
                    if "/feed/" in current_url:
                        logger.info("Successfully logged in to LinkedIn - confirmed on feed page")
                        
                        await self.browser.contexts[0].storage_state(path="linkedin_state.json")
                        return True
                    else:
                        logger.error(f"Navigation completed but not on feed page. Current URL: {current_url}")
                        return False
                except Exception as e:
                    logger.error(f"Timeout waiting for feed page: {e}")
                    return False
                    
            except Exception as e:
                logger.error(f"Login failed: {e}")
                return False

    async def search_jobs(self, keywords: str, location: str = "") -> List[JobListing]:
        """
        Search for jobs on LinkedIn.
        
        Args:
            keywords: Search keywords
            location: Optional location filter
            
        Returns:
            List[JobListing]: List of found jobs
        """
        # This is a placeholder - implement your AgentQL job search logic here
        # For now, returning an empty list
        logger.info(f"Searching for jobs with keywords: {keywords}, location: {location}")
        job_listings_list = []
        try:
            await self.page.goto(JOBS_URL)
            
            # Wait for the page to be interactive instead of waiting for networkidle
            logger.info("Waiting for page to be interactive")
            await self.page.wait_for_selector("input[type='text']", timeout=1000)
            logger.info("Page is interactive")
            
            logger.info("Filling in job search form")
            form = await self.agentql_page.query_elements(JOBS_SEARCH_QUERY)
            await form.job_search_title_input.fill(keywords)
            await self.page.wait_for_timeout(1000)
            await form.job_search_location_input.fill(location)
            await form.search_button.click()

            await self.page.wait_for_selector("li.scaffold-layout__list-item.ember-view", timeout=30000)

            # Get all jobs in the page
            job_listings = await self.agentql_page.query_elements(JOB_LIST_QUERY)

            for job in job_listings.jobs:
                await job.job_title.click()
                await self.page.wait_for_timeout(1000)
                job_details = await self.agentql_page.query_elements(JOB_DETAILS_QUERY)
                job_details.share_button.click()
                await self.page.wait_for_timeout(1000)
                copy_link_button = await self.agentql_page.query_elements(SHARE_BUTTON_QUERY)
                await copy_link_button.copy_link_button.click()
                await self.page.wait_for_timeout(1000)
                job_url = await self.page.evaluate("() => navigator.clipboard.readText()")
    
                job_listing = JobListing(title=job_details.job_title.name, company=job_details.company_name.name, location=job_details.job_location.name, posted_date=job_details.job_posted_date, job_url=job_url)
                job_listings_list.append(job_listing)
 
            
        except Exception as e:
            logger.error(f"Job search failed: {e}")
            return []

        return job_listings_list










