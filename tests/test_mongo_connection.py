"""
Test MongoDB connection using configuration from .env file.
"""
import os
import unittest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class TestMongoDBConnection(unittest.TestCase):
    """Test cases for MongoDB connection."""
    
    def setUp(self):
        """Set up test environment."""
        self.mongo_url = os.getenv("MONGO_URL")
        self.mongo_user = os.getenv("MONGO_USER")
        self.mongo_password = os.getenv("MONGO_PASSWORD")
        self.mongo_db = os.getenv("MONGO_DB", "jobs_alerts")
        
        print(f"\nTesting connection to MongoDB...")
        print(f"Database: {self.mongo_db}")
        
        # Construct the full MongoDB URL with credentials if provided
        if self.mongo_user and self.mongo_password:
            # Handle mongodb+srv:// URLs differently
            if self.mongo_url.startswith("mongodb+srv://"):
                # Extract the hostname part
                hostname = self.mongo_url.split("mongodb+srv://")[-1]
                # Construct the URL with credentials
                self.mongo_url = f"mongodb+srv://{self.mongo_user}:{self.mongo_password}@{hostname}"
            else:
                self.mongo_url = self.mongo_url.replace("mongodb://", f"mongodb://{self.mongo_user}:{self.mongo_password}@")
        
        print(f"Connection URL: {self.mongo_url}")
        self.client = None
    
    async def async_test_connection(self):
        """Test MongoDB connection."""
        try:
            # Create a new client
            self.client = AsyncIOMotorClient(self.mongo_url)
            
            # Test the connection by pinging the server
            await self.client.admin.command('ping')
            
            # If we get here, the connection was successful
            print("\nSuccessfully connected to MongoDB!")
            
            # Test database access
            db = self.client[self.mongo_db]
            collections = await db.list_collection_names()
            print(f"Available collections in {self.mongo_db}: {collections}")
            
            self.assertTrue(True, "Successfully connected to MongoDB")
            
        except ServerSelectionTimeoutError as e:
            self.fail(f"Failed to connect to MongoDB: {e}")
        except Exception as e:
            self.fail(f"Unexpected error: {e}")
        finally:
            if self.client:
                self.client.close()
    
    def test_connection(self):
        """Run the async connection test."""
        asyncio.run(self.async_test_connection())

if __name__ == '__main__':
    unittest.main() 