import httpx
import os
from typing import Any
from shared.data import SearchJobsParams

# Use environment variable or default to localhost for local development
SCRAPER_BASE_URL = os.getenv("SCRAPER_SERVICE_URL")

async def search_jobs_via_scraper(params: SearchJobsParams) -> Any:
    """
    Search jobs via scraper service.
    
    Args:
        params: SearchJobsParams containing all search parameters
    """
    # Convert SearchJobsParams to JSON
    json_data = params.model_dump(exclude_none=True)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{SCRAPER_BASE_URL}/search_jobs", json=json_data)
        return response

async def check_proxy_connection_via_scraper() -> dict[str, Any]:
    """Check proxy connection via scraper service."""
    timeout = httpx.Timeout(100.0) 
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(f"{SCRAPER_BASE_URL}/check_proxy_connection")
        response.raise_for_status()
        return response.json()
