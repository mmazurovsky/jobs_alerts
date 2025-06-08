import httpx
import os
from typing import Any

# Use environment variable or default to localhost for local development
SCRAPER_BASE_URL = os.getenv("SCRAPER_SERVICE_URL", "http://localhost:8002")

async def search_jobs_via_scraper(params: dict[str, Any]) -> Any:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{SCRAPER_BASE_URL}/search_jobs", params=params)
        response.raise_for_status()
        return response.json()

async def check_proxy_connection_via_scraper() -> dict[str, Any]:
    """Check proxy connection via scraper service."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{SCRAPER_BASE_URL}/check_proxy_connection")
        response.raise_for_status()
        return response.json()
