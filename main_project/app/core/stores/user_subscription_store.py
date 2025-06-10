"""
User subscription MongoDB store methods.
"""
from typing import List, Optional
from pymongo.errors import ServerSelectionTimeoutError
from shared.data import UserSubscription
from main_project.app.core.mongo_connection import MongoConnection
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class UserSubscriptionStore:
    def __init__(self, mongo_connection: MongoConnection) -> None:
        self.mongo_connection = mongo_connection
        self.collection = None

    async def connect(self) -> None:
        self.collection = self.mongo_connection.db.user_subscriptions
        await self.collection.create_index("user_id", unique=True)
        await self.collection.create_index("end_date")
        await self.collection.create_index([("is_active", 1), ("end_date", 1)])

    async def get_user_subscription(self, user_id: int) -> Optional[UserSubscription]:
        """Get current subscription for user."""
        if not self.mongo_connection._connected:
            raise ServerSelectionTimeoutError("Not connected to MongoDB")
        
        try:
            doc = await self.collection.find_one({"user_id": user_id})
            if doc:
                doc.pop('_id', None)
                # Convert string dates back to datetime objects
                if isinstance(doc.get('start_date'), str):
                    doc['start_date'] = datetime.fromisoformat(doc['start_date'].replace('Z', '+00:00'))
                if isinstance(doc.get('end_date'), str):
                    doc['end_date'] = datetime.fromisoformat(doc['end_date'].replace('Z', '+00:00'))
                if isinstance(doc.get('created_at'), str):
                    doc['created_at'] = datetime.fromisoformat(doc['created_at'].replace('Z', '+00:00'))
                if isinstance(doc.get('updated_at'), str):
                    doc['updated_at'] = datetime.fromisoformat(doc['updated_at'].replace('Z', '+00:00'))
                return UserSubscription(**doc)
            return None
        except Exception as e:
            logger.error(f"Error getting user subscription for user {user_id}: {e}")
            return None

    async def save_user_subscription(self, subscription: UserSubscription) -> None:
        """Save or update user subscription."""
        if not self.mongo_connection._connected:
            raise ServerSelectionTimeoutError("Not connected to MongoDB")
        
        try:
            subscription.updated_at = datetime.now(timezone.utc)
            subscription_dict = subscription.model_dump(mode="json")
            
            await self.collection.update_one(
                {"user_id": subscription.user_id},
                {"$set": subscription_dict},
                upsert=True
            )
            logger.info(f"Saved subscription for user {subscription.user_id}: {subscription.subscription_type}")
        except Exception as e:
            logger.error(f"Error saving subscription for user {subscription.user_id}: {e}")
            raise

    async def get_expired_subscriptions(self) -> List[UserSubscription]:
        """Get all expired but still active subscriptions."""
        if not self.mongo_connection._connected:
            raise ServerSelectionTimeoutError("Not connected to MongoDB")
        
        try:
            now = datetime.now(timezone.utc)
            cursor = self.collection.find({
                "is_active": True,
                "end_date": {"$lt": now}
            })
            
            subscriptions = []
            async for doc in cursor:
                doc.pop('_id', None)
                # Convert string dates back to datetime objects
                if isinstance(doc.get('start_date'), str):
                    doc['start_date'] = datetime.fromisoformat(doc['start_date'].replace('Z', '+00:00'))
                if isinstance(doc.get('end_date'), str):
                    doc['end_date'] = datetime.fromisoformat(doc['end_date'].replace('Z', '+00:00'))
                if isinstance(doc.get('created_at'), str):
                    doc['created_at'] = datetime.fromisoformat(doc['created_at'].replace('Z', '+00:00'))
                if isinstance(doc.get('updated_at'), str):
                    doc['updated_at'] = datetime.fromisoformat(doc['updated_at'].replace('Z', '+00:00'))
                subscriptions.append(UserSubscription(**doc))
            return subscriptions
        except Exception as e:
            logger.error(f"Error getting expired subscriptions: {e}")
            return []

    async def get_subscriptions_ending_on_date(self, target_date: datetime, subscription_type: str) -> List[UserSubscription]:
        """Get subscriptions ending on specific date."""
        if not self.mongo_connection._connected:
            raise ServerSelectionTimeoutError("Not connected to MongoDB")
        
        try:
            start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            cursor = self.collection.find({
                "is_active": True,
                "subscription_type": subscription_type,
                "end_date": {"$gte": start_of_day, "$lte": end_of_day}
            })
            
            subscriptions = []
            async for doc in cursor:
                doc.pop('_id', None)
                # Convert string dates back to datetime objects
                if isinstance(doc.get('start_date'), str):
                    doc['start_date'] = datetime.fromisoformat(doc['start_date'].replace('Z', '+00:00'))
                if isinstance(doc.get('end_date'), str):
                    doc['end_date'] = datetime.fromisoformat(doc['end_date'].replace('Z', '+00:00'))
                if isinstance(doc.get('created_at'), str):
                    doc['created_at'] = datetime.fromisoformat(doc['created_at'].replace('Z', '+00:00'))
                if isinstance(doc.get('updated_at'), str):
                    doc['updated_at'] = datetime.fromisoformat(doc['updated_at'].replace('Z', '+00:00'))
                subscriptions.append(UserSubscription(**doc))
            return subscriptions
        except Exception as e:
            logger.error(f"Error getting subscriptions ending on date {target_date}: {e}")
            return []

    async def deactivate_subscription(self, user_id: int) -> None:
        """Mark subscription as inactive."""
        if not self.mongo_connection._connected:
            raise ServerSelectionTimeoutError("Not connected to MongoDB")
        
        try:
            await self.collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "is_active": False,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            logger.info(f"Deactivated subscription for user {user_id}")
        except Exception as e:
            logger.error(f"Error deactivating subscription for user {user_id}: {e}")
            raise 