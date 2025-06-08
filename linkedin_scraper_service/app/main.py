import logging
logging.basicConfig(level=logging.INFO)
logging.info("main.py module imported and executed.")

from fastapi import FastAPI, Query, HTTPException
from linkedin_scraper_service.app.scraper import LinkedInScraperGuest
from shared.data import SearchJobsParams, TimePeriod, JobType, RemoteType
from typing import Optional

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