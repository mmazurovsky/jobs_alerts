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

@app.get("/search_jobs")
async def search_jobs(
    keywords: str = Query(...),
    location: str = Query(...),
    time_period: str = Query(...),
    job_type: list[str] = Query(...),
    remote_type: list[str] = Query(...),
    callback_url: str = Query(...),
    job_search_id: str = Query(...),
    user_id: int = Query(...),
    filter_text: str = Query(...),
):
    logger.info(f"/search_jobs called with: keywords={keywords}, location={location}, time_period={time_period}, job_type={job_type}, remote_type={remote_type}")
    
    try:
        # Create SearchJobsParams directly
        search_params = SearchJobsParams(
            keywords=keywords,
            location=location,
            time_period=time_period,
            job_types=job_type,
            remote_types=remote_type,
            callback_url=callback_url,
            job_search_id=job_search_id,
            user_id=user_id,
            filter_text=filter_text,
        )
    except Exception as e:
        logger.error(f"Failed to create SearchJobsParams: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    
    # Parse time_period if needed
    tp = search_params.time_period
    if tp and isinstance(tp, str):
        tp = TimePeriod.parse(tp)

    job_types = [JobType.parse(jt) for jt in search_params.job_types] if isinstance(search_params.job_types, list) else [JobType.parse(search_params.job_types)]
    remote_types = [RemoteType.parse(rt) for rt in search_params.remote_types] if isinstance(search_params.remote_types, list) else [RemoteType.parse(search_params.remote_types)]
    
    scraper = await LinkedInScraperGuest.create_new_session()
    jobs = await scraper.search_jobs(
        keywords=search_params.keywords,
        location=search_params.location,
        time_period=tp,
        job_types=job_types,
        remote_types=remote_types,
        user_id=search_params.user_id,
        filter_text=search_params.filter_text,
    )
    return [job.model_dump() for job in jobs] if jobs else []

@app.post("/search_jobs")
async def search_jobs(
    request: Request
):
    data = await request.json()
    try:
        # Deserialize directly to SearchJobsParams
        search_params = SearchJobsParams.model_validate(data)
    except Exception as e:
        logger.error(f"Failed to parse SearchJobsParams: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    
    # Parse time_period if needed
    tp = search_params.time_period
    if tp and isinstance(tp, str):
        tp = TimePeriod.parse(tp)

    job_types = [JobType.parse(jt) for jt in search_params.job_types] if isinstance(search_params.job_types, list) else [JobType.parse(search_params.job_types)]
    remote_types = [RemoteType.parse(rt) for rt in search_params.remote_types] if isinstance(search_params.remote_types, list) else [RemoteType.parse(search_params.remote_types)]

    async def run_job():
        try:
            callback_url = search_params.callback_url
            job_search_id = search_params.job_search_id
            user_id = search_params.user_id
            
            if not callback_url or not isinstance(callback_url, str):
                logger.error(f"Invalid callback_url: {callback_url} for user_id={user_id}, job_search_id={job_search_id}")
                return
            logger.info(f"[search_jobs] Starting job for user_id={user_id}, job_search_id={job_search_id}, keywords={search_params.keywords}, location={search_params.location}, callback_url={callback_url}")
            scraper = await LinkedInScraperGuest.create_new_session()
            jobs = await scraper.search_jobs(
                keywords=search_params.keywords,
                location=search_params.location,
                time_period=tp,
                job_types=job_types,
                remote_types=remote_types,
                user_id=user_id,
                filter_text=search_params.filter_text,

            )
            logger.info(f"[search_jobs] Finished job for user_id={user_id}, keywords={search_params.keywords}, location={search_params.location}, job_search_id={job_search_id}, found {len(jobs) if jobs else 0} jobs")
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