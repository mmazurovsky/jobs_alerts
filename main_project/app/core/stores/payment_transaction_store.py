"""
Payment transaction MongoDB store methods.
"""
from typing import List, Optional
from pymongo.errors import ServerSelectionTimeoutError
from shared.data import PaymentTransaction
from main_project.app.core.mongo_connection import MongoConnection
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class PaymentTransactionStore:
    def __init__(self, mongo_connection: MongoConnection) -> None:
        self.mongo_connection = mongo_connection
        self.collection = None

    async def connect(self) -> None:
        self.collection = self.mongo_connection.db.payment_transactions
        await self.collection.create_index("transaction_id", unique=True)
        await self.collection.create_index("user_id")
        await self.collection.create_index("telegram_payment_charge_id")
        await self.collection.create_index("status")

    async def save_transaction(self, transaction: PaymentTransaction) -> None:
        """Save payment transaction."""
        if not self.mongo_connection._connected:
            raise ServerSelectionTimeoutError("Not connected to MongoDB")
        
        try:
            transaction_dict = transaction.model_dump(mode="json")
            await self.collection.insert_one(transaction_dict)
            logger.info(f"Saved transaction {transaction.transaction_id} for user {transaction.user_id}")
        except Exception as e:
            logger.error(f"Error saving transaction {transaction.transaction_id}: {e}")
            raise

    async def get_transaction(self, transaction_id: str) -> Optional[PaymentTransaction]:
        """Get transaction by ID."""
        if not self.mongo_connection._connected:
            raise ServerSelectionTimeoutError("Not connected to MongoDB")
        
        try:
            doc = await self.collection.find_one({"transaction_id": transaction_id})
            if doc:
                doc.pop('_id', None)
                # Convert string dates back to datetime objects
                if isinstance(doc.get('created_at'), str):
                    doc['created_at'] = datetime.fromisoformat(doc['created_at'].replace('Z', '+00:00'))
                if isinstance(doc.get('updated_at'), str):
                    doc['updated_at'] = datetime.fromisoformat(doc['updated_at'].replace('Z', '+00:00'))
                return PaymentTransaction(**doc)
            return None
        except Exception as e:
            logger.error(f"Error getting transaction {transaction_id}: {e}")
            return None

    async def update_transaction_status(
        self, 
        transaction_id: str, 
        status: str, 
        payment_charge_id: Optional[str] = None
    ) -> None:
        """Update transaction status."""
        if not self.mongo_connection._connected:
            raise ServerSelectionTimeoutError("Not connected to MongoDB")
        
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            if payment_charge_id:
                update_data["telegram_payment_charge_id"] = payment_charge_id
                
            await self.collection.update_one(
                {"transaction_id": transaction_id},
                {"$set": update_data}
            )
            logger.info(f"Updated transaction {transaction_id} status to {status}")
        except Exception as e:
            logger.error(f"Error updating transaction {transaction_id}: {e}")
            raise

    async def get_pending_transactions_for_user(self, user_id: int) -> List[PaymentTransaction]:
        """Get pending transactions for user."""
        if not self.mongo_connection._connected:
            raise ServerSelectionTimeoutError("Not connected to MongoDB")
        
        try:
            cursor = self.collection.find({
                "user_id": user_id,
                "status": "pending"
            })
            
            transactions = []
            async for doc in cursor:
                doc.pop('_id', None)
                # Convert string dates back to datetime objects
                if isinstance(doc.get('created_at'), str):
                    doc['created_at'] = datetime.fromisoformat(doc['created_at'].replace('Z', '+00:00'))
                if isinstance(doc.get('updated_at'), str):
                    doc['updated_at'] = datetime.fromisoformat(doc['updated_at'].replace('Z', '+00:00'))
                transactions.append(PaymentTransaction(**doc))
            return transactions
        except Exception as e:
            logger.error(f"Error getting pending transactions for user {user_id}: {e}")
            return []

    async def get_completed_payments_without_subscription_update(self) -> List[PaymentTransaction]:
        """Find completed payments that might need recovery."""
        if not self.mongo_connection._connected:
            raise ServerSelectionTimeoutError("Not connected to MongoDB")
        
        try:
            # Find completed transactions older than 5 minutes
            five_minutes_ago = datetime.now(timezone.utc).replace(microsecond=0) - datetime.timedelta(minutes=5)
            
            cursor = self.collection.find({
                "status": "completed",
                "created_at": {"$lt": five_minutes_ago.isoformat()}
            })
            
            transactions = []
            async for doc in cursor:
                doc.pop('_id', None)
                # Convert string dates back to datetime objects
                if isinstance(doc.get('created_at'), str):
                    doc['created_at'] = datetime.fromisoformat(doc['created_at'].replace('Z', '+00:00'))
                if isinstance(doc.get('updated_at'), str):
                    doc['updated_at'] = datetime.fromisoformat(doc['updated_at'].replace('Z', '+00:00'))
                transactions.append(PaymentTransaction(**doc))
            return transactions
        except Exception as e:
            logger.error(f"Error getting completed payments for recovery: {e}")
            return []

    async def mark_payment_recovered(self, transaction_id: str) -> None:
        """Mark payment as recovered (add metadata)."""
        if not self.mongo_connection._connected:
            raise ServerSelectionTimeoutError("Not connected to MongoDB")
        
        try:
            await self.collection.update_one(
                {"transaction_id": transaction_id},
                {
                    "$set": {
                        "recovered_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            logger.info(f"Marked transaction {transaction_id} as recovered")
        except Exception as e:
            logger.error(f"Error marking transaction {transaction_id} as recovered: {e}")
            raise 