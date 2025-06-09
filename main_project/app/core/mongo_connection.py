"""
MongoDB connection logic for reuse.
"""
import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

class MongoConnection:
    def __init__(self):
        self.client = None
        self.db = None
        self._connected = False

    async def connect(self):
        try:
            mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            mongo_user = os.getenv("MONGO_USER")
            mongo_password = os.getenv("MONGO_PASSWORD")
            mongo_db = os.getenv("MONGO_DB", "jobs_alerts")

            if mongo_user and mongo_password:
                if mongo_url.startswith("mongodb+srv://"):
                    hostname = mongo_url.split("mongodb+srv://")[-1]
                    mongo_url = f"mongodb+srv://{mongo_user}:{mongo_password}@{hostname}"
                else:
                    mongo_url = mongo_url.replace("mongodb://", f"mongodb://{mongo_user}:{mongo_password}@")

            self.client = AsyncIOMotorClient(mongo_url)
            self.db = self.client[mongo_db]
            await self.client.admin.command('ping')
            self._connected = True
            logger.info("Successfully connected to MongoDB")
        except ServerSelectionTimeoutError as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def close(self):
        if self.client:
            self.client.close()
            self._connected = False
            logger.info("Closed MongoDB connection") 