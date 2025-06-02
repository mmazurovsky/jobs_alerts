"""
Sent jobs MongoDB store methods.
"""
from typing import List
from pymongo.errors import ServerSelectionTimeoutError
from src.data.data import SentJobOut
from src.data.mongo_connection import MongoConnection
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class SentJobsStore:
    def __init__(self, mongo_connection: MongoConnection):
        self.mongo_connection = mongo_connection
        self.collection = None

    async def connect(self):
        self.collection = self.mongo_connection.db.sent_jobs
        # Ensure user_id is indexed (non-unique)
        await self.collection.create_index("user_id", unique=False)

    async def save_sent_job(self, user_id: int, job_url: str) -> None:
        if not self.mongo_connection._connected:
            raise ServerSelectionTimeoutError("Not connected to MongoDB")
        sent_job = SentJobOut(user_id=user_id, job_url=job_url, sent_at=datetime.now(timezone.utc))
        await self.collection.insert_one(sent_job.__dict__)
        logger.info(f"Saved sent job for user {user_id}: {job_url}")

    async def get_sent_jobs_for_user(self, user_id: int) -> List[SentJobOut]:
        if not self.mongo_connection._connected:
            raise ServerSelectionTimeoutError("Not connected to MongoDB")
        cursor = self.collection.find({"user_id": user_id})
        jobs = []
        async for doc in cursor:
            doc.pop('_id', None)
            jobs.append(SentJobOut(**doc))
        return jobs

    async def was_job_sent(self, user_id: int, job_url: str) -> bool:
        if not self.mongo_connection._connected:
            raise ServerSelectionTimeoutError("Not connected to MongoDB")
        doc = await self.collection.find_one({"user_id": user_id, "job_url": job_url})
        if doc:
            doc.pop('_id', None)
        return doc is not None 