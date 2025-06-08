"""
Main application module.
"""
import asyncio
import logging
import os
import signal
import sys
from typing import Optional
from pathlib import Path
import threading
from fastapi import FastAPI, Query
import uvicorn
from dotenv import load_dotenv

from main_project.app.core.container import get_container
from main_project.app.utils.logging_config import setup_logging
from main_project.app.scraper_client import search_jobs_via_scraper, check_proxy_connection_via_scraper

# Configure logging to file and console
setup_logging(log_file=Path('logs/app.log'))
log_level = os.getenv('LOG_LEVEL', 'INFO')
logging.getLogger().setLevel(log_level)

# Disable DEBUG logs from other libraries unless explicitly requested
if log_level != 'DEBUG':
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('pymongo').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('apscheduler').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Define FastAPI app instance for ASGI
app = FastAPI(title="Main Project API", description="Jobs Alerts Main Service")

@app.get("/")
async def root():
    return {"message": "Jobs Alerts Main Service", "status": "running"}

@app.get("/healthz")
async def health():
    return {"status": "ok"}

async def handle_shutdown(signum: int, frame: Optional[object]) -> None:
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    container = get_container()
    await container.shutdown()
    sys.exit(0)

async def main() -> None:
    """Main application entry point."""
    container = None
    try:
        # Get container and initialize services
        container = get_container()
        await container.initialize()

        # Proxy connection check via HTTP
        try:
            proxy_result = await check_proxy_connection_via_scraper()
            if proxy_result.get("success"):
                logger.info("Proxy connection test succeeded via scraper service.")
            else:
                logger.error("Proxy connection test failed via scraper service.")
        except Exception as e:
            logger.error(f"Failed to check proxy connection via scraper service: {e}")
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(handle_shutdown(s, f)))
        signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(handle_shutdown(s, f)))
        
        # Keep the application running
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"Application error: {e}")
        if container:
            await container.shutdown()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 