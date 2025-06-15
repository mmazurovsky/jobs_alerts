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
from fastapi import FastAPI, Query, Request
import uvicorn

from main_project.app.core.container import get_container
from main_project.app.utils.logging_config import setup_logging
from main_project.app.scraper_client import search_jobs_via_scraper, check_proxy_connection_via_scraper
from shared.data import JobSearchOut, StreamEvent, StreamType, FullJobListing

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

@app.on_event("startup")
async def on_startup():
    container = get_container()
    await container.initialize()
    # Optionally: check proxy connection here if you want
    try:
        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                proxy_result = await check_proxy_connection_via_scraper()
                if proxy_result.get("success"):
                    logger.info("Proxy connection test succeeded via scraper service.")
                    break
                else:
                    logger.error("Proxy connection test failed via scraper service.")
            except Exception as e:
                logger.error(f"Attempt {attempt}/{max_retries}: Failed to check proxy connection via scraper service: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(3)
                else:
                    logger.error("Giving up after maximum retry attempts to connect to scraper service.")
    except Exception as e:
        logger.error(f"Failed to check proxy connection via scraper service", exc_info=True)

@app.on_event("shutdown")
async def on_shutdown():
    container = get_container()
    await container.shutdown()

@app.get("/")
async def root():
    return {"message": "Jobs Alerts Main Service", "status": "running"}

@app.get("/healthz")
async def health():
    return {"status": "ok"}

@app.post("/job_results_callback")
async def job_results_callback(request: Request):
    data = await request.json()
    job_search_id = data.get("job_search_id")
    user_id = data.get("user_id")
    jobs = data.get("jobs")
    logger.info(f"Received job_results_callback: job_search_id={job_search_id}, user_id={user_id}, jobs_count={len(jobs) if jobs else 0}")
    # Convert jobs to list of FullJobListing at the start
    parsed_jobs = [FullJobListing.model_validate(job) for job in jobs] if jobs else []
    container = get_container()
    sent_jobs_store = container.sent_jobs_store
    stream_manager = container.stream_manager
    job_search_store = container.job_search_store

    # Fetch job search parameters from MongoDB
    job_search: Optional[JobSearchOut] = await job_search_store.get_search_by_id(job_search_id)

    if not parsed_jobs:
        logger.info(f"No jobs received for job_search_id={job_search_id}, user_id={user_id}")
    if parsed_jobs:
        sent_jobs = await sent_jobs_store.get_sent_jobs_for_user(user_id)
        sent_job_urls = {job.job_url for job in sent_jobs}
        new_jobs = [job for job in parsed_jobs if job.link not in sent_job_urls]
        logger.info(f"Found {len(new_jobs)} new jobs for job_search_id={job_search_id}, user_id={user_id}")
        if new_jobs:
            # Format header with search params
            if job_search:
                message = (
                    f"🔔 New job listings found for:\n"
                    f"Keywords: {job_search.job_title}\n"
                    f"Location: {job_search.location}\n"
                    f"Job Types: {', '.join([jt.label for jt in job_search.job_types])}\n"
                    f"Remote Types: {', '.join([rt.label for rt in job_search.remote_types])}\n\n"
                )
            else:
                message = "🔔 New job listings found for your search.\n\n"
            for job in new_jobs:
                message += (
                    f"Compatibility: {job.compatibility_score}\n"
                    f"Title: {job.title}\n"
                    f"Employer: {job.company}\n"
                    f"Techstack: {', '.join(job.techstack)}\n"
                    f"Location: {job.location}\n"
                    f"Created: {job.created_ago}\n"
                    f"🔗: {job.link}\n\n"
                )
            for job in new_jobs:
                await sent_jobs_store.save_sent_job(user_id, job.link)
            message_data = {
                "user_id": user_id,
                "message": message
            }
            stream_manager.publish(StreamEvent(
                type=StreamType.SEND_MESSAGE,
                data=message_data,
                source="job_search_scheduler"
            ))
    return {"status": "received"}

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
            max_retries = 10
            for attempt in range(1, max_retries + 1):
                try:
                    proxy_result = await check_proxy_connection_via_scraper()
                    if proxy_result.get("success"):
                        logger.info("Proxy connection test succeeded via scraper service.")
                        break
                    else:
                        logger.error("Proxy connection test failed via scraper service.")
                except Exception as e:
                    logger.error(f"Attempt {attempt}/{max_retries}: Failed to check proxy connection via scraper service: {e}")
                    if attempt < max_retries:
                        await asyncio.sleep(3)
                    else:
                        logger.error("Giving up after maximum retry attempts to connect to scraper service.")
        except Exception as e:
            logger.error(f"Failed to check proxy connection via scraper service", exc_info=True)
        
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