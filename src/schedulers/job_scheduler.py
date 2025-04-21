"""
Job scheduler implementation using APScheduler.
"""
import logging
from typing import Callable, Awaitable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler = AsyncIOScheduler()
_is_running = False


def start_scheduler(job: Callable[[], Awaitable[None]], interval_minutes: int = 5) -> None:
    """
    Start the scheduler with the given job.
    
    Args:
        job: An async function to be executed periodically
        interval_minutes: Interval between job executions in minutes
    """
    global _is_running
    
    if _is_running:
        logger.warning("Scheduler is already running")
        return

    # Add the job to the scheduler
    _scheduler.add_job(
        job,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id='linkedin_scraper',
        name='LinkedIn Job Scraper',
        replace_existing=True
    )

    # Start the scheduler
    _scheduler.start()
    _is_running = True
    logger.info(f"Scheduler started with interval of {interval_minutes} minutes")


def stop_scheduler() -> None:
    """Stop the scheduler."""
    global _is_running
    
    if not _is_running:
        return

    _scheduler.shutdown()
    _is_running = False
    logger.info("Scheduler stopped") 