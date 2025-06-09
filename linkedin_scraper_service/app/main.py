import logging
logging.basicConfig(level=logging.INFO)
logging.info("main.py module imported and executed.")

from fastapi import FastAPI, Query, HTTPException, Request, Body
from linkedin_scraper_service.app.scraper import LinkedInScraperGuest
from shared.data import SearchJobsParams, TimePeriod, JobType, RemoteType
from typing import Optional
import asyncio
import httpx

app = FastAPI()

logger = logging.getLogger("search_jobs_endpoint")

@app.get("/search_jobs")
async def search_jobs(
    keywords: str = Query(...),
    location: str = Query(...),
    time_period: str = Query(...),
    job_type: list[str] = Query(...),
    remote_type: list[str] = Query(...),
):
    logger.info(f"/search_jobs called with: keywords={keywords}, location={location}, time_period={time_period}, job_type={job_type}, remote_type={remote_type}")
    try:
        params = SearchJobsParams(
            keywords=keywords,
            location=location,
            time_period=time_period,
            job_type=job_type,
            remote_type=remote_type,
        )
    except Exception as e:
        logger.error(f"Failed to parse SearchJobsParams: {e}")
        raise HTTPException(status_code=422, detail=str(e))

    scraper = await LinkedInScraperGuest.create_new_session()
    results = await scraper.search_jobs(
        keywords=params.keywords,
        location=params.location,
        time_period=TimePeriod.parse(params.time_period),
        job_types=[JobType.parse(jt) for jt in params.job_type] if isinstance(params.job_type, list) else [JobType.parse(params.job_type)],
        remote_types=[RemoteType.parse(rt) for rt in params.remote_type] if isinstance(params.remote_type, list) else [RemoteType.parse(params.remote_type)],
    )
    return results

@app.post("/search_jobs")
async def search_jobs(
    request: Request
):
    data = await request.json()
    keywords = data.get("keywords")
    location = data.get("location")
    time_period = data.get("time_period")
    job_type = data.get("job_type")
    remote_type = data.get("remote_type")
    callback_url = data.get("callback_url")
    job_search_id = data.get("job_search_id")
    user_id = data.get("user_id")

    # Return 200 immediately
    # Run the job in the background
    async def run_job():
        try:
            if not callback_url or not isinstance(callback_url, str):
                logger.error(f"Invalid callback_url: {callback_url} for user_id={user_id}, job_search_id={job_search_id}")
                return
            params = {
                "keywords": keywords,
                "location": location,
                "time_period": time_period,
                "job_type": job_type,
                "remote_type": remote_type,
                "user_id": user_id,
                "job_search_id": job_search_id,
            }
            logger.info(f"[search_jobs] Starting job for user_id={user_id}, job_search_id={job_search_id}, keywords={keywords}, location={location}, callback_url={callback_url}")
            scraper = await LinkedInScraperGuest.create_new_session()
            jobs = await scraper.search_jobs(params)
            logger.info(f"[search_jobs] Finished job for user_id={user_id}, job_search_id={job_search_id}, found {len(jobs) if jobs else 0} jobs")
            async with httpx.AsyncClient() as client:
                await client.post(callback_url, json={
                    "job_search_id": job_search_id,
                    "user_id": user_id,
                    "jobs": jobs or [],
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