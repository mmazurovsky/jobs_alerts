"""
Premium subscription service for managing user subscriptions and limits.
"""
from typing import Dict, Optional, Tuple
from datetime import datetime, timezone, timedelta
import logging

from shared.data import UserSubscription
from main_project.app.core.stores.user_subscription_store import UserSubscriptionStore
from main_project.app.core.stores.job_search_store import JobSearchStore

logger = logging.getLogger(__name__)

class PremiumService:
    def __init__(
        self, 
        user_subscription_store: UserSubscriptionStore, 
        job_search_store: JobSearchStore
    ) -> None:
        self.user_subscription_store = user_subscription_store
        self.job_search_store = job_search_store
        
        # Subscription limits configuration
        self.subscription_limits = {
            "trial": 1,
            "premium_week": 12,
            "premium_month": 12
        }
        
    async def create_trial_if_first_user(self, user_id: int) -> Optional[UserSubscription]:
        """Create trial subscription for first-time users."""
        try:
            # Check if user already has a subscription
            existing = await self.user_subscription_store.get_user_subscription(user_id)
            if existing:
                return existing
                
            # Create new trial subscription
            now = datetime.now(timezone.utc)
            trial_subscription = UserSubscription(
                user_id=user_id,
                subscription_type="trial",
                start_date=now,
                end_date=now + timedelta(days=7),
                is_active=True,
                telegram_payment_charge_id=None
            )
            
            await self.user_subscription_store.save_user_subscription(trial_subscription)
            logger.info(f"Created trial subscription for user {user_id}")
            
            return trial_subscription
        except Exception as e:
            logger.error(f"Error creating trial for user {user_id}: {e}")
            return None

    async def check_user_can_create_job(self, user_id: int) -> Tuple[bool, str]:
        """Check if user can create a new job search."""
        try:
            subscription = await self.user_subscription_store.get_user_subscription(user_id)
            active_jobs = await self.job_search_store.get_active_job_count(user_id)
            
            # If no subscription and no jobs, they can create their first job (trial will be created)
            if not subscription and active_jobs == 0:
                return True, ""
                
            # If no subscription but has jobs, something is wrong
            if not subscription and active_jobs > 0:
                return False, "❌ No active subscription found. Please contact support."
                
            # Check if subscription is expired
            now = datetime.now(timezone.utc)
            if subscription.end_date < now:
                # Process expired subscription immediately
                await self._process_expired_subscription_immediately(user_id)
                return False, (
                    "⏰ Your subscription has expired!\n\n"
                    "Your existing job searches have been paused. "
                    "Upgrade to Premium to reactivate them and create new ones."
                )
                
            # Check job limits based on subscription type
            max_jobs = self.get_max_searches_for_subscription(subscription.subscription_type)
            
            if active_jobs >= max_jobs:
                if subscription.subscription_type == "trial":
                    return False, (
                        f"🔒 Trial users can only have {max_jobs} active job search.\n\n"
                        "Upgrade to Premium to create up to 12 searches!"
                    )
                else:
                    return False, (
                        f"🔒 You've reached your limit of {max_jobs} active searches.\n\n"
                        "Delete an existing search to create a new one, or upgrade your plan."
                    )
                    
            return True, ""
        except Exception as e:
            logger.error(f"Error checking job creation limits for user {user_id}: {e}")
            return False, "❌ Error checking your subscription. Please try again later."
            
    async def _process_expired_subscription_immediately(self, user_id: int) -> None:
        """Process expired subscription immediately when detected."""
        try:
            await self.user_subscription_store.deactivate_subscription(user_id)
            await self.job_search_store.deactivate_excess_searches(user_id, keep_count=1)
            logger.info(f"Processed expired subscription for user {user_id}")
        except Exception as e:
            logger.error(f"Error processing expired subscription for user {user_id}: {e}")
        
    def get_max_searches_for_subscription(self, subscription_type: Optional[str]) -> int:
        """Get maximum allowed searches for subscription type."""
        if not subscription_type:
            return 0
        return self.subscription_limits.get(subscription_type, 0)

    async def get_premium_status(self, user_id: int) -> Dict[str, any]:
        """Get comprehensive premium status for user."""
        try:
            subscription = await self.user_subscription_store.get_user_subscription(user_id)
            active_searches = await self.job_search_store.get_active_job_count(user_id)
            
            if not subscription:
                return {
                    "status": "No subscription",
                    "plan_name": "None",
                    "active_searches": active_searches,
                    "max_searches": 0,
                    "expires_at": None,
                    "days_remaining": None,
                    "can_upgrade": True,
                    "can_renew": False
                }
                
            now = datetime.now(timezone.utc)
            days_remaining = (subscription.end_date - now).days if subscription.end_date > now else 0
            
            plan_names = {
                "trial": "Free Trial",
                "premium_week": "Premium (1 Week)",
                "premium_month": "Premium (1 Month)"
            }
            
            status = "Active" if subscription.is_active and subscription.end_date > now else "Expired"
            max_searches = self.get_max_searches_for_subscription(subscription.subscription_type)
            
            return {
                "status": status,
                "plan_name": plan_names.get(subscription.subscription_type, subscription.subscription_type),
                "active_searches": active_searches,
                "max_searches": max_searches,
                "expires_at": subscription.end_date.strftime("%Y-%m-%d %H:%M UTC"),
                "days_remaining": max(0, days_remaining),
                "can_upgrade": subscription.subscription_type == "trial" or status == "Expired",
                "can_renew": subscription.subscription_type.startswith("premium") and status == "Active"
            }
        except Exception as e:
            logger.error(f"Error getting premium status for user {user_id}: {e}")
            return {
                "status": "Error",
                "plan_name": "Unknown",
                "active_searches": 0,
                "max_searches": 0,
                "expires_at": None,
                "days_remaining": None,
                "can_upgrade": False,
                "can_renew": False
            }

    async def deactivate_excess_searches(self, user_id: int) -> int:
        """Deactivate excess searches when subscription expires."""
        try:
            return await self.job_search_store.deactivate_excess_searches(user_id, keep_count=1)
        except Exception as e:
            logger.error(f"Error deactivating excess searches for user {user_id}: {e}")
            return 0

    async def reactivate_user_searches(self, user_id: int) -> int:
        """Reactivate user searches up to their subscription limit."""
        try:
            subscription = await self.user_subscription_store.get_user_subscription(user_id)
            if not subscription:
                return 0
                
            max_searches = self.get_max_searches_for_subscription(subscription.subscription_type)
            return await self.job_search_store.reactivate_user_searches(user_id, max_count=max_searches)
        except Exception as e:
            logger.error(f"Error reactivating searches for user {user_id}: {e}")
            return 0

    async def get_user_subscription(self, user_id: int) -> Optional[UserSubscription]:
        """Get user subscription."""
        return await self.user_subscription_store.get_user_subscription(user_id)

    async def process_expired_subscriptions(self) -> None:
        """Process all expired subscriptions."""
        try:
            expired_subscriptions = await self.user_subscription_store.get_expired_subscriptions()
            
            for subscription in expired_subscriptions:
                try:
                    await self._process_expired_subscription_immediately(subscription.user_id)
                except Exception as e:
                    logger.error(f"Failed to process expired subscription for user {subscription.user_id}: {e}")
                    
            logger.info(f"Processed {len(expired_subscriptions)} expired subscriptions")
        except Exception as e:
            logger.error(f"Error processing expired subscriptions: {e}") 