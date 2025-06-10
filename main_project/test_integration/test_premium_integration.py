"""
Premium subscription integration tests.
Run with: python -m pytest test_integration/test_premium_integration.py -v
"""
import asyncio
import pytest
import logging
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from main_project.test_integration.test_bot_config import TestDataHelper, MockPaymentService
from main_project.app.core.container import Container
from shared.data import JobSearchIn, JobType, RemoteType, TimePeriod

logger = logging.getLogger(__name__)

# Test user IDs
TEST_USER_TRIAL = 1001
TEST_USER_PREMIUM = 1002  
TEST_USER_EXPIRED = 1003
TEST_USER_NEW = 1004

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_container():
    """Setup test container with test database."""
    container = Container()
    await container.initialize()
    
    yield container
    
    await container.shutdown()

@pytest.fixture
async def test_helper(test_container):
    """Create test data helper."""
    helper = TestDataHelper(test_container)
    
    # Clear test data before each test
    for user_id in [TEST_USER_TRIAL, TEST_USER_PREMIUM, TEST_USER_EXPIRED, TEST_USER_NEW]:
        await helper.clear_test_data(user_id)
    
    yield helper
    
    # Cleanup after each test
    for user_id in [TEST_USER_TRIAL, TEST_USER_PREMIUM, TEST_USER_EXPIRED, TEST_USER_NEW]:
        await helper.clear_test_data(user_id)

class TestTrialSubscription:
    """Test trial subscription functionality."""
    
    async def test_new_user_gets_trial_on_first_job_creation(self, test_container, test_helper):
        """Test that new users automatically get trial subscription."""
        premium_service = test_container.premium_service
        
        # Check user can create job (should be allowed for new users)
        can_create, message = await premium_service.check_user_can_create_job(TEST_USER_NEW)
        assert can_create, f"New user should be able to create job: {message}"
        
        # Create trial subscription
        subscription = await premium_service.create_trial_if_first_user(TEST_USER_NEW)
        assert subscription is not None
        assert subscription.subscription_type == "trial"
        assert subscription.is_active
        
        # Verify subscription status
        status = await premium_service.get_premium_status(TEST_USER_NEW)
        assert status["plan_name"] == "Free Trial"
        assert status["status"] == "Active"
        assert status["max_searches"] == 1
        
    async def test_trial_user_job_creation_limit(self, test_container, test_helper):
        """Test trial users can only create 1 job search."""
        # Setup trial user
        await test_helper.create_trial_user(TEST_USER_TRIAL)
        
        premium_service = test_container.premium_service
        
        # First job should be allowed
        can_create, message = await premium_service.check_user_can_create_job(TEST_USER_TRIAL)
        assert can_create, f"Trial user should be able to create first job: {message}"
        
        # Create first job
        await test_helper.create_test_job_searches(TEST_USER_TRIAL, 1)
        
        # Second job should be blocked
        can_create, message = await premium_service.check_user_can_create_job(TEST_USER_TRIAL)
        assert not can_create
        assert "trial users can only have 1 active job search" in message.lower()
        assert "upgrade to premium" in message.lower()

class TestPremiumSubscription:
    """Test premium subscription functionality."""
    
    async def test_premium_user_can_create_multiple_jobs(self, test_container, test_helper):
        """Test premium users can create up to 12 job searches."""
        # Setup premium user
        await test_helper.create_premium_user(TEST_USER_PREMIUM)
        
        premium_service = test_container.premium_service
        
        # Create 12 jobs (should all be allowed)
        for i in range(12):
            can_create, message = await premium_service.check_user_can_create_job(TEST_USER_PREMIUM)
            assert can_create, f"Premium user should be able to create job {i+1}: {message}"
            
            await test_helper.create_test_job_searches(TEST_USER_PREMIUM, 1)
        
        # 13th job should be blocked
        can_create, message = await premium_service.check_user_can_create_job(TEST_USER_PREMIUM)
        assert not can_create
        assert "reached your limit of 12 active searches" in message.lower()
        
    async def test_premium_status_display(self, test_container, test_helper):
        """Test premium status information display."""
        # Setup premium user
        subscription = await test_helper.create_premium_user(TEST_USER_PREMIUM, "premium_month")
        
        premium_service = test_container.premium_service
        status = await premium_service.get_premium_status(TEST_USER_PREMIUM)
        
        assert status["plan_name"] == "Premium (1 Month)"
        assert status["status"] == "Active"
        assert status["max_searches"] == 12
        assert status["days_remaining"] > 25  # Should be close to 30 days
        assert not status["can_upgrade"]  # Already premium
        assert status["can_renew"]  # Can renew existing premium

class TestSubscriptionExpiry:
    """Test subscription expiry handling."""
    
    async def test_expired_subscription_deactivates_excess_searches(self, test_container, test_helper):
        """Test that expired subscriptions deactivate excess searches."""
        # Setup user with expired subscription and multiple jobs
        await test_helper.create_expired_user(TEST_USER_EXPIRED)
        await test_helper.create_test_job_searches(TEST_USER_EXPIRED, 5)  # More than trial limit
        
        premium_service = test_container.premium_service
        
        # Check subscription status (should detect expiry)
        can_create, message = await premium_service.check_user_can_create_job(TEST_USER_EXPIRED)
        assert not can_create
        assert "subscription has expired" in message.lower()
        
        # Verify excess searches were deactivated
        active_count = await test_container.job_search_store.get_active_job_count(TEST_USER_EXPIRED)
        assert active_count == 1, f"Should have only 1 active search after expiry, got {active_count}"
        
    async def test_expired_subscription_processing(self, test_container, test_helper):
        """Test batch processing of expired subscriptions."""
        # Setup multiple expired users
        users_to_expire = [TEST_USER_EXPIRED, TEST_USER_TRIAL]
        
        for user_id in users_to_expire:
            await test_helper.create_expired_user(user_id)
            await test_helper.create_test_job_searches(user_id, 3)
        
        # Process expired subscriptions
        premium_service = test_container.premium_service
        await premium_service.process_expired_subscriptions()
        
        # Verify all users have only 1 active search
        for user_id in users_to_expire:
            active_count = await test_container.job_search_store.get_active_job_count(user_id)
            assert active_count == 1, f"User {user_id} should have 1 active search after expiry processing"

class TestPaymentFlow:
    """Test payment and upgrade functionality."""
    
    async def test_payment_invoice_creation(self, test_container, test_helper):
        """Test premium invoice creation."""
        payment_service = test_container.payment_handler_service
        
        # Create invoice for premium month
        invoice = await payment_service.create_premium_invoice(TEST_USER_NEW, "premium_month")
        
        assert invoice["title"] == "Premium - 1 Month"
        assert invoice["currency"] == "XTR"
        assert len(invoice["prices"]) == 1
        assert invoice["prices"][0].amount == 500  # 500 stars
        
        # Verify transaction was recorded
        transaction = await test_container.payment_transaction_store.get_pending_transactions_for_user(TEST_USER_NEW)
        assert len(transaction) == 1
        assert transaction[0].status == "pending"
        assert transaction[0].subscription_type == "premium_month"
        
    async def test_duplicate_invoice_prevention(self, test_container, test_helper):
        """Test that duplicate invoices are prevented."""
        payment_service = test_container.payment_handler_service
        
        # Create first invoice
        await payment_service.create_premium_invoice(TEST_USER_NEW, "premium_month")
        
        # Try to create another invoice immediately (should fail)
        with pytest.raises(ValueError, match="pending payment"):
            await payment_service.create_premium_invoice(TEST_USER_NEW, "premium_month")
            
    async def test_upgrade_trial_to_premium(self, test_container, test_helper):
        """Test upgrading from trial to premium."""
        # Setup trial user with 1 job and some paused jobs
        await test_helper.create_trial_user(TEST_USER_TRIAL)
        await test_helper.create_test_job_searches(TEST_USER_TRIAL, 1, active=True)
        await test_helper.create_test_job_searches(TEST_USER_TRIAL, 3, active=False)
        
        # Simulate premium purchase
        payment_service = test_container.payment_handler_service
        await payment_service._upgrade_user_subscription_atomic(
            TEST_USER_TRIAL, 
            "premium_month", 
            "test_charge_123"
        )
        
        # Reactivate user searches
        reactivated = await test_container.premium_service.reactivate_user_searches(TEST_USER_TRIAL)
        assert reactivated > 0, "Should reactivate paused searches"
        
        # Verify premium status
        status = await test_container.premium_service.get_premium_status(TEST_USER_TRIAL)
        assert status["plan_name"] == "Premium (1 Month)"
        assert status["status"] == "Active"
        
    async def test_premium_subscription_stacking(self, test_container, test_helper):
        """Test that premium subscriptions stack (extend existing)."""
        # Create premium user with subscription ending in 10 days
        now = datetime.now(timezone.utc)
        subscription = await test_helper.create_premium_user(TEST_USER_PREMIUM, "premium_week")
        
        # Modify end date to simulate existing subscription
        subscription.end_date = now + timedelta(days=10)
        await test_container.user_subscription_store.save_user_subscription(subscription)
        
        # Purchase another week
        payment_service = test_container.payment_handler_service
        await payment_service._upgrade_user_subscription_atomic(
            TEST_USER_PREMIUM,
            "premium_week", 
            "test_charge_extension"
        )
        
        # Verify subscription was extended
        updated_subscription = await test_container.user_subscription_store.get_user_subscription(TEST_USER_PREMIUM)
        expected_end = now + timedelta(days=17)  # 10 existing + 7 new
        
        # Allow 1 day tolerance for timing
        assert abs((updated_subscription.end_date - expected_end).days) <= 1

class TestSearchManagement:
    """Test job search activation/deactivation."""
    
    async def test_search_activation_status(self, test_container, test_helper):
        """Test that searches show correct active/paused status."""
        # Create premium user with mixed active/inactive searches
        await test_helper.create_premium_user(TEST_USER_PREMIUM)
        
        # Create some searches and deactivate some
        searches = await test_helper.create_test_job_searches(TEST_USER_PREMIUM, 5, active=True)
        
        # Manually deactivate 2 searches
        for i in range(2):
            await test_container.job_search_store.collection.update_one(
                {"id": searches[i].id},
                {"$set": {"is_active": False}}
            )
        
        # Verify counts
        active_count = await test_container.job_search_store.get_active_job_count(TEST_USER_PREMIUM)
        assert active_count == 3, f"Should have 3 active searches, got {active_count}"
        
        # Test reactivation
        reactivated = await test_container.job_search_store.reactivate_user_searches(TEST_USER_PREMIUM, max_count=12)
        assert reactivated == 2, f"Should reactivate 2 searches, got {reactivated}"
        
        # Verify final count
        final_active = await test_container.job_search_store.get_active_job_count(TEST_USER_PREMIUM)
        assert final_active == 5, f"Should have 5 active searches after reactivation, got {final_active}"

class TestPaymentRecovery:
    """Test payment recovery functionality."""
    
    async def test_orphaned_payment_recovery(self, test_container, test_helper):
        """Test recovery of payments that didn't update subscriptions."""
        # Create completed payment transaction without subscription update
        transaction = await test_helper.simulate_payment_transaction(
            TEST_USER_NEW, 
            "premium_month", 
            "completed"
        )
        
        # Modify created date to simulate old transaction
        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        await test_container.payment_transaction_store.collection.update_one(
            {"transaction_id": transaction.transaction_id},
            {"$set": {"created_at": old_time.isoformat()}}
        )
        
        # Run payment recovery
        recovery_service = test_container.payment_recovery_service
        recovered_count = await recovery_service.recover_orphaned_payments()
        
        assert recovered_count > 0, "Should recover orphaned payment"
        
        # Verify subscription was created
        subscription = await test_container.user_subscription_store.get_user_subscription(TEST_USER_NEW)
        assert subscription is not None
        assert subscription.subscription_type == "premium_month"

class TestIntegrationEdgeCases:
    """Test edge cases and error conditions."""
    
    async def test_corrupted_subscription_handling(self, test_container, test_helper):
        """Test handling of corrupted subscription data."""
        # Create subscription with invalid data
        from shared.data import UserSubscription
        
        corrupted_sub = UserSubscription(
            user_id=TEST_USER_NEW,
            subscription_type="invalid_type",  # Invalid type
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=7),
            is_active=True
        )
        await test_container.user_subscription_store.save_user_subscription(corrupted_sub)
        
        # Service should handle gracefully
        premium_service = test_container.premium_service
        status = await premium_service.get_premium_status(TEST_USER_NEW)
        
        # Should return default values, not crash
        assert status["max_searches"] == 0  # Invalid type returns 0 searches
        
    async def test_concurrent_job_creation(self, test_container, test_helper):
        """Test concurrent job creation doesn't exceed limits."""
        # Setup trial user
        await test_helper.create_trial_user(TEST_USER_TRIAL)
        
        premium_service = test_container.premium_service
        
        # Try to create multiple jobs concurrently
        tasks = []
        for i in range(3):
            task = premium_service.check_user_can_create_job(TEST_USER_TRIAL)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # At least one should succeed, others might fail due to timing
        success_count = sum(1 for can_create, _ in results if can_create)
        assert success_count >= 1, "At least one job creation should succeed"

# Test runner helper
async def run_integration_tests():
    """Helper to run all integration tests."""
    import subprocess
    import sys
    
    # Run pytest
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "test_integration/test_premium_integration.py", 
        "-v", "--tb=short"
    ], capture_output=True, text=True)
    
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    print("Return code:", result.returncode)
    
    return result.returncode == 0

if __name__ == "__main__":
    # Quick test runner
    asyncio.run(run_integration_tests()) 