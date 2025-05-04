"""
MongoDB manager for job searches.
"""
import os
import logging
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from dataclasses import asdict

from src.data.data import JobSearchOut

logger = logging.getLogger(__name__)

class MongoManager:
    """Manager for MongoDB operations."""
    
    def __init__(self):
        """Initialize MongoDB connection."""
        self.client = None
        self.db = None
        self.collection = None
        self._connected = False
    
    async def connect(self) -> None:
        """Connect to MongoDB using environment variables."""
        try:
            mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            mongo_user = os.getenv("MONGO_USER")
            mongo_password = os.getenv("MONGO_PASSWORD")
            mongo_db = os.getenv("MONGO_DB", "jobs_alerts")
            
            if mongo_user and mongo_password:
                # Handle mongodb+srv:// URLs differently
                if mongo_url.startswith("mongodb+srv://"):
                    # Extract the hostname part
                    hostname = mongo_url.split("mongodb+srv://")[-1]
                    # Construct the URL with credentials
                    mongo_url = f"mongodb+srv://{mongo_user}:{mongo_password}@{hostname}"
                else:
                    mongo_url = mongo_url.replace("mongodb://", f"mongodb://{mongo_user}:{mongo_password}@")
            
            self.client = AsyncIOMotorClient(mongo_url)
            self.db = self.client[mongo_db]
            self.collection = self.db.job_searches
            
            # Test connection
            await self.client.admin.command('ping')
            self._connected = True
            logger.info("Successfully connected to MongoDB")
            
        except ServerSelectionTimeoutError as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def close(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self._connected = False
            logger.info("Closed MongoDB connection")
    
    async def get_user_searches(self, user_id: int) -> List[JobSearchOut]:
        """Get all job searches for a user."""
        if not self._connected:
            raise ServerSelectionTimeoutError("Not connected to MongoDB")
        
        try:
            cursor = self.collection.find({"user_id": user_id})
            searches = []
            async for doc in cursor:
                searches.append(JobSearchOut(**doc))
            return searches
        except Exception as e:
            logger.error(f"Error getting user searches: {e}")
            return []
    
    async def delete_search(self, search_id: str) -> bool:
        """Delete a job search."""
        if not self._connected:
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
        """Get all job searches from the database."""
        if not self._connected:
            raise ServerSelectionTimeoutError("Not connected to MongoDB")
        
        try:
            cursor = self.collection.find()
            searches = []
            async for doc in cursor:
                searches.append(JobSearchOut(**doc))
            return searches
        except Exception as e:
            logger.error(f"Error getting all searches: {e}")
            return []
    
    async def save_job_search(self, job_search: JobSearchOut) -> None:
        """Save a job search to MongoDB."""
        try:
            # Convert to dict with proper serialization
            job_search_dict = job_search.model_dump(mode="json")
            
            # Update or insert the job search
            await self.collection.update_one(
                {"id": job_search.id},
                {"$set": job_search_dict},
                upsert=True
            )
            logger.info(f"Saved job search {job_search.id} to MongoDB")
        except Exception as e:
            logger.error(f"Error saving job search to MongoDB: {e}")
            raise 