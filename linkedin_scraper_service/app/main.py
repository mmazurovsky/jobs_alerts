import logging
logging.basicConfig(level=logging.INFO)
logging.info("main.py module imported and executed.")

from fastapi import FastAPI, Query, HTTPException, Request, Body
from linkedin_scraper_service.app.scraper import LinkedInScraperGuest
from shared.data import SearchJobsParams, TimePeriod, JobType, RemoteType
from typing import Optional, List, Dict, Any
import asyncio
import httpx

app = FastAPI()

logger = logging.getLogger("search_jobs_endpoint")

def parse_search_jobs_params(
    keywords: str,
    location: str,
    time_period: str,
    job_type: list,
    remote_type: list,
) -> dict:
    try:
        params = SearchJobsParams(
            keywords=keywords,
            location=location,
            time_period=time_period,
            job_types=job_type,
            remote_types=remote_type,
        )
    except Exception as e:
        logger.error(f"Failed to parse SearchJobsParams: {e}")
        raise HTTPException(status_code=422, detail=str(e))

    # Parse time_period if needed
    tp = params.time_period
    if tp and isinstance(tp, str):
        tp = TimePeriod.parse(tp)

    job_types = [JobType.parse(jt) for jt in params.job_types] if isinstance(params.job_types, list) else [JobType.parse(params.job_types)]
    remote_types = [RemoteType.parse(rt) for rt in params.remote_types] if isinstance(params.remote_types, list) else [RemoteType.parse(params.remote_types)]

    return {
        "keywords": params.keywords,
        "location": params.location,
        "time_period": tp,
        "job_types": job_types,
        "remote_types": remote_types,
    }

@app.get("/search_jobs")
async def search_jobs(
    keywords: str = Query(...),
    location: str = Query(...),
    time_period: str = Query(...),
    job_type: list[str] = Query(...),
    remote_type: list[str] = Query(...),
):
    logger.info(f"/search_jobs called with: keywords={keywords}, location={location}, time_period={time_period}, job_type={job_type}, remote_type={remote_type}")
    parsed = parse_search_jobs_params(
        keywords=keywords,
        location=location,
        time_period=time_period,
        job_type=job_type,
        remote_type=remote_type,
    )
    scraper = await LinkedInScraperGuest.create_new_session()
    jobs = await scraper.search_jobs(
        keywords=parsed["keywords"],
        location=parsed["location"],
        time_period=parsed["time_period"],
        job_types=parsed["job_types"],
        remote_types=parsed["remote_types"],
    )
    return [job.model_dump() for job in jobs] if jobs else []

@app.post("/search_jobs")
async def search_jobs(
    request: Request
):
    data = await request.json()
    parsed = parse_search_jobs_params(
        keywords=data.get("keywords"),
        location=data.get("location"),
        time_period=data.get("time_period"),
        job_type=data.get("job_types", []),
        remote_type=data.get("remote_types", []),
    )
    callback_url = data.get("callback_url")
    job_search_id = data.get("job_search_id")
    user_id = data.get("user_id")

    async def run_job():
        try:
            if not callback_url or not isinstance(callback_url, str):
                logger.error(f"Invalid callback_url: {callback_url} for user_id={user_id}, job_search_id={job_search_id}")
                return
            logger.info(f"[search_jobs] Starting job for user_id={user_id}, job_search_id={job_search_id}, keywords={parsed['keywords']}, location={parsed['location']}, callback_url={callback_url}")
            scraper = await LinkedInScraperGuest.create_new_session()
            jobs = await scraper.search_jobs(
                keywords=parsed["keywords"],
                location=parsed["location"],
                time_period=parsed["time_period"],
                job_types=parsed["job_types"],
                remote_types=parsed["remote_types"],
                user_id=user_id,
            )
            logger.info(f"[search_jobs] Finished job for user_id={user_id}, keywords={parsed['keywords']}, location={parsed['location']}, job_search_id={job_search_id}, found {len(jobs) if jobs else 0} jobs")
            async with httpx.AsyncClient() as client:
                await client.post(callback_url, json={
                    "job_search_id": job_search_id,
                    "user_id": user_id,
                    "jobs": [job.model_dump() for job in jobs] if jobs else [],
                })
        except Exception as e:
            logger.error(f"Error in background job for user_id={user_id}, job_search_id={job_search_id}, callback_url={callback_url}: {e}", exc_info=True)
    asyncio.create_task(run_job())
    return {}

@app.get("/check_proxy_connection")
async def check_proxy_connection():
    """Check if proxy connection is working."""
    try:
        scraper = LinkedInScraperGuest(name="proxy_test")
        proxy_ok = await scraper.check_proxy_connection()
        return {
            "proxy_status": "ok" if proxy_ok else "failed",
            "success": proxy_ok
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy check failed: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    await LinkedInScraperGuest.close_all_browsers() 