"""
Manual test bot for interactive premium testing.
Run with: python test_integration/test_bot_manual.py

This creates a test bot connected to a test database for manual testing of:
- Trial subscriptions
- Premium upgrades  
- Job search limits
- Payment flows (mocked)
- Search activation/deactivation

Set environment variables
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone, timedelta

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main_project.test_integration.test_bot_config import TestDataHelper, MockPaymentService
from main_project.app.core.container import Container
from shared.data import UserSubscription

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestBotController:
    """Controller for manual test bot operations."""
    
    def __init__(self):
        self.container = None
        self.test_helper = None
        self.mock_payment = None
        
    async def start(self):
        """Start the test bot."""
        logger.info("🚀 Starting Test Bot for Premium Features...")
        
        # Initialize container
        self.container = Container()
        await self.container.initialize()
        
        # Setup test helper
        self.test_helper = TestDataHelper(self.container)
        
        # Setup mock payment service (optional)
        self.mock_payment = MockPaymentService(self.container.payment_handler_service)
        
        logger.info("✅ Test bot initialized successfully!")
        logger.info(f"📊 Database: {os.getenv('MONGO_URL')}")
        logger.info(f"🤖 Bot Token: {os.getenv('TELEGRAM_BOT_TOKEN')[:10]}...")
        
        # Display test commands
        self.show_test_commands()
        
        # Start bot
        await self.container.telegram_bot.initialize()
        
        logger.info("🎯 Test bot is running! Use the commands above to test premium features.")
        logger.info("💡 Tip: Use /premium to check subscription status anytime")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Stopping test bot...")
            await self.stop()
    
    async def stop(self):
        """Stop the test bot."""
        if self.container:
            await self.container.shutdown()
    
    def show_test_commands(self):
        """Display available test commands and scenarios."""
        print("\n" + "="*60)
        print("🧪 PREMIUM FEATURES TEST SCENARIOS")
        print("="*60)
        
        print("\n📋 **Basic Bot Commands:**")
        print("  /start     - Start conversation")
        print("  /help      - Show help")
        print("  /premium   - View premium status & upgrade options")
        print("  /new       - Create new job search (tests limits)")
        print("  /list      - List job searches (shows active/paused)")
        print("  /delete    - Delete job search")
        
        print("\n🔬 **Test Scenarios to Try:**")
        print("  1️⃣  New User Trial:")
        print("      • Use /new to create first job → Gets 7-day trial")
        print("      • Try /new again → Should be blocked with upgrade prompt")
        print("      • Use /premium to see trial status")
        
        print("\n  2️⃣  Premium Upgrade:")
        print("      • Click upgrade buttons in /premium")
        print("      • Test payment flow (mocked)")
        print("      • Verify increased limits after upgrade")
        
        print("\n  3️⃣  Search Limits:")
        print("      • Premium users: Create up to 12 searches")
        print("      • Trial users: Limited to 1 search")
        print("      • Use /list to see active vs paused searches")
        
        print("\n  4️⃣  Expiry Testing:")
        print("      • Use helper commands below to simulate expired users")
        print("      • Check that excess searches get paused")
        
        print("\n🛠️  **Test Helper Commands (run in Python console):**")
        print("  # Connect to test bot:")
        print("  >>> controller = TestBotController()")
        print("  >>> await controller.start()")
        print("")
        print("  # Create test scenarios:")
        print("  >>> await controller.setup_expired_user(USER_ID)")
        print("  >>> await controller.setup_premium_user(USER_ID)")
        print("  >>> await controller.setup_trial_user(USER_ID)")
        print("  >>> await controller.clear_user_data(USER_ID)")
        print("")
        print("  # Simulate payment completion:")
        print("  >>> await controller.simulate_payment(USER_ID, 'premium_month')")
        
        print("\n" + "="*60)
        print("💡 Replace USER_ID with your Telegram user ID")
        print("💡 Use @userinfobot on Telegram to get your user ID")
        print("=" * 60 + "\n")
    
    async def setup_trial_user(self, user_id: int):
        """Setup a user with trial subscription."""
        await self.test_helper.clear_test_data(user_id)
        subscription = await self.test_helper.create_trial_user(user_id)
        logger.info(f"✅ Created trial user {user_id}, expires: {subscription.end_date}")
        return subscription
    
    async def setup_premium_user(self, user_id: int, subscription_type: str = "premium_month"):
        """Setup a user with premium subscription."""
        await self.test_helper.clear_test_data(user_id)
        subscription = await self.test_helper.create_premium_user(user_id, subscription_type)
        logger.info(f"✅ Created premium user {user_id}, expires: {subscription.end_date}")
        return subscription
    
    async def setup_expired_user(self, user_id: int):
        """Setup a user with expired subscription and multiple searches."""
        await self.test_helper.clear_test_data(user_id)
        subscription = await self.test_helper.create_expired_user(user_id)
        searches = await self.test_helper.create_test_job_searches(user_id, 5)
        logger.info(f"✅ Created expired user {user_id} with {len(searches)} searches")
        logger.info("💡 Use /new to trigger expiry detection and search deactivation")
        return subscription, searches
    
    async def clear_user_data(self, user_id: int):
        """Clear all data for a user."""
        await self.test_helper.clear_test_data(user_id)
        logger.info(f"🗑️  Cleared all data for user {user_id}")
    
    async def simulate_payment(self, user_id: int, subscription_type: str):
        """Simulate successful payment completion."""
        try:
            # Simulate payment processing
            await self.container.payment_handler_service._upgrade_user_subscription_atomic(
                user_id, 
                subscription_type, 
                f"test_charge_{user_id}_{int(datetime.now().timestamp())}"
            )
            
            # Reactivate searches
            reactivated = await self.container.premium_service.reactivate_user_searches(user_id)
            
            logger.info(f"💰 Simulated payment for user {user_id}: {subscription_type}")
            logger.info(f"🔄 Reactivated {reactivated} searches")
            
            # Show updated status
            status = await self.container.premium_service.get_premium_status(user_id)
            logger.info(f"📊 New status: {status['plan_name']} - {status['status']}")
            
        except Exception as e:
            logger.error(f"❌ Error simulating payment: {e}")
    
    async def run_expiry_check(self):
        """Manually run expired subscription processing."""
        logger.info("🔍 Running expired subscription check...")
        await self.container.premium_service.process_expired_subscriptions()
        logger.info("✅ Expiry check completed")
    
    async def run_payment_recovery(self):
        """Manually run payment recovery."""
        logger.info("🔧 Running payment recovery...")
        recovered = await self.container.payment_recovery_service.recover_orphaned_payments()
        logger.info(f"✅ Payment recovery completed, recovered {recovered} payments")

async def main():
    """Main entry point for test bot."""
    controller = TestBotController()
    await controller.start()

if __name__ == "__main__":
    if not os.getenv('TELEGRAM_BOT_TOKEN'):
        print("❌ Error: TELEGRAM_BOT_TOKEN environment variable required")
        print("💡 Get a test bot token from @BotFather on Telegram")
        sys.exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Test bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting test bot: {e}")
        sys.exit(1) 