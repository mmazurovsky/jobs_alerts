"""
Test bot configuration for integration testing.
"""
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from shared.data import UserSubscription, PaymentTransaction, JobSearchOut
from main_project.app.core.container import Container

logger = logging.getLogger(__name__)

class TestDataHelper:
    """Helper for creating test data and scenarios."""
    
    def __init__(self, container: Container):
        self.container = container
        
    async def clear_test_data(self, user_id: int):
        """Clear all test data for a user."""
        try:
            # Clear job searches
            searches = await self.container.job_search_store.get_user_searches(user_id)
            for search in searches:
                await self.container.job_search_store.delete_search(search.id)
            
            # Clear subscription
            await self.container.user_subscription_store.collection.delete_many({"user_id": user_id})
            
            # Clear payment transactions
            await self.container.payment_transaction_store.collection.delete_many({"user_id": user_id})
            
            # Clear sent jobs
            await self.container.sent_jobs_store.collection.delete_many({"user_id": user_id})
            
            logger.info(f"Cleared test data for user {user_id}")
        except Exception as e:
            logger.error(f"Error clearing test data: {e}")
    
    async def create_trial_user(self, user_id: int) -> UserSubscription:
        """Create a user with trial subscription."""
        now = datetime.now(timezone.utc)
        trial = UserSubscription(
            user_id=user_id,
            subscription_type="trial",
            start_date=now,
            end_date=now + timedelta(days=7),
            is_active=True
        )
        await self.container.user_subscription_store.save_user_subscription(trial)
        return trial
    
    async def create_premium_user(self, user_id: int, subscription_type: str = "premium_month") -> UserSubscription:
        """Create a user with premium subscription."""
        now = datetime.now(timezone.utc)
        duration = 30 if subscription_type == "premium_month" else 7
        premium = UserSubscription(
            user_id=user_id,
            subscription_type=subscription_type,
            start_date=now,
            end_date=now + timedelta(days=duration),
            is_active=True,
            telegram_payment_charge_id="test_charge_id"
        )
        await self.container.user_subscription_store.save_user_subscription(premium)
        return premium
    
    async def create_expired_user(self, user_id: int) -> UserSubscription:
        """Create a user with expired subscription."""
        now = datetime.now(timezone.utc)
        expired = UserSubscription(
            user_id=user_id,
            subscription_type="trial",
            start_date=now - timedelta(days=10),
            end_date=now - timedelta(days=3),
            is_active=True  # Will be detected as expired
        )
        await self.container.user_subscription_store.save_user_subscription(expired)
        return expired
    
    async def create_test_job_searches(self, user_id: int, count: int, active: bool = True) -> List[JobSearchOut]:
        """Create multiple test job searches for a user."""
        from shared.data import JobSearchIn, JobType, RemoteType, TimePeriod
        
        searches = []
        for i in range(count):
            search_in = JobSearchIn(
                job_title=f"Test Job {i+1}",
                location="Test Location",
                job_types=[JobType.FULL_TIME],
                remote_types=[RemoteType.REMOTE],
                time_period=TimePeriod.FIVE_MINUTES,
                user_id=user_id,
                blacklist=[]
            )
            
            search_id = await self.container.job_search_manager.add_search(search_in)
            
            # Set active status if needed
            if not active:
                await self.container.job_search_store.collection.update_one(
                    {"id": search_id},
                    {"$set": {"is_active": False}}
                )
            
            search = await self.container.job_search_store.get_search_by_id(search_id)
            searches.append(search)
        
        return searches
    
    async def simulate_payment_transaction(self, user_id: int, subscription_type: str, status: str = "completed") -> PaymentTransaction:
        """Create a test payment transaction."""
        transaction = PaymentTransaction(
            user_id=user_id,
            transaction_id=f"test_{user_id}_{int(datetime.now().timestamp())}",
            amount_stars=350 if subscription_type == "premium_week" else 500,
            subscription_type=subscription_type,
            status=status,
            telegram_payment_charge_id=f"test_charge_{user_id}",
            invoice_payload='{"test": "payload"}'
        )
        await self.container.payment_transaction_store.save_transaction(transaction)
        return transaction

class MockPaymentService:
    """Mock payment service for testing without real payments."""
    
    def __init__(self, payment_handler_service):
        self.original_service = payment_handler_service
        self.mock_enabled = False
        
    def enable_mock(self):
        """Enable mock mode for testing."""
        self.mock_enabled = True
        
    def disable_mock(self):
        """Disable mock mode."""
        self.mock_enabled = False
        
    async def create_premium_invoice(self, user_id: int, subscription_type: str):
        """Mock invoice creation that always succeeds."""
        if self.mock_enabled:
            return {
                "title": f"Test {subscription_type}",
                "description": "Test premium subscription",
                "payload": '{"test": "mock_payload"}',
                "currency": "XTR",
                "prices": [{"label": "Test", "amount": 100}],
                "start_parameter": f"test_{subscription_type}",
                "need_name": False,
                "need_phone_number": False,
                "need_email": False,
                "need_shipping_address": False,
                "send_phone_number_to_provider": False,
                "send_email_to_provider": False,
                "is_flexible": False
            }
        return await self.original_service.create_premium_invoice(user_id, subscription_type) 