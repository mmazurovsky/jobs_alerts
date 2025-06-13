"""
Job search MongoDB store methods.
"""
from typing import List, Optional
from pymongo.errors import ServerSelectionTimeoutError
from shared.data import JobSearchOut
from main_project.app.core.mongo_connection import MongoConnection
import logging

logger = logging.getLogger(__name__)

class JobSearchStore:
    def __init__(self, mongo_connection: MongoConnection):
        self.mongo_connection = mongo_connection
        self.collection = None

    async def connect(self):
        self.collection = self.mongo_connection.db.job_searches
        await self.collection.create_index("id", unique=True)
        await self.collection.create_index("user_id", unique=False)

    async def get_user_searches(self, user_id: int) -> List[JobSearchOut]:
        if not self.mongo_connection._connected:
            raise ServerSelectionTimeoutError("Not connected to MongoDB")
        try:
            cursor = self.collection.find({"user_id": user_id})
            searches = []
            async for doc in cursor:
                doc.pop('_id', None)
                searches.append(JobSearchOut(**doc))
            return searches
        except Exception as e:
            logger.error(f"Error getting user searches: {e}")
            return []

    async def delete_search(self, search_id: str) -> bool:
        if not self.mongo_connection._connected:
            raise ServerSelectionTimeoutError("Not connected to MongoDB")
        try:
            result = await self.collection.delete_one({"id": search_id})
            if result.deleted_count > 0:
                logger.info(f"Deleted job search {search_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting job search: {e}")
            return False

    async def get_all_searches(self) -> List[JobSearchOut]:
        if not self.mongo_connection._connected:
            raise ServerSelectionTimeoutError("Not connected to MongoDB")
        try:
            cursor = self.collection.find()
            searches = []
            async for doc in cursor:
                doc.pop('_id', None)
                searches.append(JobSearchOut(**doc))
            return searches
        except Exception as e:
            logger.error(f"Error getting all searches: {e}")
            return []

    async def save_job_search(self, job_search: JobSearchOut) -> None:
        try:
            job_search_dict = job_search.model_dump(mode="json")
            await self.collection.update_one(
                {"id": job_search.id},
                {"$set": job_search_dict},
                upsert=True
            )
            logger.info(f"Saved job search {job_search.id} to MongoDB")
        except Exception as e:
            logger.error(f"Error saving job search to MongoDB: {e}")
            raise

    async def get_search_by_id(self, search_id: str) -> Optional[JobSearchOut]:
        if not self.mongo_connection._connected:
            raise ServerSelectionTimeoutError("Not connected to MongoDB")
        try:
            doc = await self.collection.find_one({"id": search_id})
            if doc:
                doc.pop('_id', None)
                return JobSearchOut(**doc)
            return None
        except Exception as e:
            logger.error(f"Error getting job search by id: {e}")
            return None 