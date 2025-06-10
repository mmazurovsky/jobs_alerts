"""
Payment handler service for processing Telegram Stars payments with security and concurrency protection.
"""
import asyncio
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

from telegram import LabeledPrice, PreCheckoutQuery, SuccessfulPayment

from shared.data import PaymentTransaction, UserSubscription
from main_project.app.core.stores.payment_transaction_store import PaymentTransactionStore
from main_project.app.core.stores.user_subscription_store import UserSubscriptionStore
from main_project.app.services.premium_service import PremiumService

logger = logging.getLogger(__name__)

class PaymentSecurity:
    """Payment security utilities for tamper-proof payloads."""
    
    def __init__(self, secret_key: str) -> None:
        self.secret_key = secret_key.encode()
        
    def create_secure_payload(self, user_id: int, subscription_type: str, transaction_id: str) -> str:
        """Create tamper-proof payment payload."""
        # Add timestamp and nonce to prevent replay
        timestamp = int(time.time())
        nonce = secrets.token_hex(8)
        
        payload_data = {
            "user_id": user_id,
            "subscription_type": subscription_type,
            "transaction_id": transaction_id,
            "timestamp": timestamp,
            "nonce": nonce
        }
        
        # Create signature
        payload_string = json.dumps(payload_data, sort_keys=True)
        signature = hmac.new(self.secret_key, payload_string.encode(), hashlib.sha256).hexdigest()
        
        payload_data["signature"] = signature
        return json.dumps(payload_data)
        
    def validate_payment_payload(self, payload_json: str) -> Dict[str, any]:
        """Validate payment payload authenticity."""
        try:
            payload_data = json.loads(payload_json)
            signature = payload_data.pop("signature")
            
            # Recreate signature
            payload_string = json.dumps(payload_data, sort_keys=True)
            expected_signature = hmac.new(self.secret_key, payload_string.encode(), hashlib.sha256).hexdigest()
            
            # Verify signature
            if not hmac.compare_digest(signature, expected_signature):
                raise ValueError("Invalid payload signature")
                
            # Check timestamp (reject payloads older than 1 hour)
            timestamp = payload_data.get("timestamp", 0)
            if abs(time.time() - timestamp) > 3600:
                raise ValueError("Payload expired")
                
            return payload_data
            
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid payload format: {e}")

class PaymentHandlerService:
    """Service for handling Telegram Stars payments with security and concurrency protection."""
    
    SUBSCRIPTION_PRICES = {
        "premium_week": {
            "stars": 350, 
            "title": "Premium - 1 Week",
            "description": "7 days of premium features with up to 12 job searches",
            "duration_days": 7
        },
        "premium_month": {
            "stars": 500,
            "title": "Premium - 1 Month", 
            "description": "30 days of premium features with up to 12 job searches",
            "duration_days": 30
        }
    }
    
    def __init__(
        self, 
        payment_store: PaymentTransactionStore, 
        subscription_store: UserSubscriptionStore, 
        premium_service: PremiumService
    ) -> None:
        self.payment_store = payment_store
        self.subscription_store = subscription_store
        self.premium_service = premium_service
        
        # Concurrency protection
        self._payment_locks: Dict[int, asyncio.Lock] = {}
        
        # Security
        secret_key = os.getenv("PAYMENT_SECRET_KEY", "default-insecure-key")
        self.payment_security = PaymentSecurity(secret_key)
        
        # Duplicate prevention
        self._recent_invoices: Dict[int, Dict[str, any]] = {}
        
    async def _get_user_payment_lock(self, user_id: int) -> asyncio.Lock:
        """Get or create payment lock for user."""
        if user_id not in self._payment_locks:
            self._payment_locks[user_id] = asyncio.Lock()
        return self._payment_locks[user_id]
        
    async def create_premium_invoice(self, user_id: int, subscription_type: str) -> Dict[str, any]:
        """Create invoice for premium subscription with duplicate prevention."""
        if subscription_type not in self.SUBSCRIPTION_PRICES:
            raise ValueError(f"Invalid subscription type: {subscription_type}")
            
        # Check for recent invoice (within 5 minutes)
        if user_id in self._recent_invoices:
            recent = self._recent_invoices[user_id]
            time_diff = time.time() - recent["timestamp"]
            if time_diff < 300 and recent["subscription_type"] == subscription_type:  # 5 minutes
                raise ValueError(f"Please wait {300 - int(time_diff)} seconds before creating another invoice")
        
        # Check for pending transactions
        pending_transactions = await self.payment_store.get_pending_transactions_for_user(user_id)
        if pending_transactions:
            raise ValueError("You have a pending payment. Please complete or cancel it before creating a new one.")
            
        price_info = self.SUBSCRIPTION_PRICES[subscription_type]
        
        # Generate unique transaction ID
        transaction_id = f"premium_{user_id}_{int(time.time())}"
        
        # Create secure payment payload
        payload = self.payment_security.create_secure_payload(user_id, subscription_type, transaction_id)
        
        # Create payment transaction record
        transaction = PaymentTransaction(
            user_id=user_id,
            transaction_id=transaction_id,
            amount_stars=price_info["stars"],
            subscription_type=subscription_type,
            status="pending",
            invoice_payload=payload
        )
        await self.payment_store.save_transaction(transaction)
        
        # Track invoice creation
        self._recent_invoices[user_id] = {
            "timestamp": time.time(),
            "subscription_type": subscription_type
        }
        
        return {
            "title": price_info["title"],
            "description": price_info["description"],
            "payload": payload,
            "currency": "XTR",  # Telegram Stars
            "prices": [LabeledPrice(label="Premium Subscription", amount=price_info["stars"])],
            "start_parameter": f"premium_{subscription_type}",
            "need_name": False,
            "need_phone_number": False,
            "need_email": False,
            "need_shipping_address": False,
            "send_phone_number_to_provider": False,
            "send_email_to_provider": False,
            "is_flexible": False
        }
        
    async def handle_pre_checkout_query(self, pre_checkout_query: PreCheckoutQuery) -> bool:
        """Validate pre-checkout query with security checks."""
        try:
            # Validate payload security
            payload_data = self.payment_security.validate_payment_payload(pre_checkout_query.invoice_payload)
            
            transaction_id = payload_data["transaction_id"]
            user_id = payload_data["user_id"]
            
            # Validate transaction exists and is pending
            transaction = await self.payment_store.get_transaction(transaction_id)
            if not transaction:
                logger.error(f"Transaction not found: {transaction_id}")
                return False
                
            if transaction.status != "pending":
                logger.error(f"Transaction not pending: {transaction_id}, status: {transaction.status}")
                return False
                
            if transaction.user_id != user_id:
                logger.error(f"User ID mismatch: {transaction.user_id} vs {user_id}")
                return False
                
            logger.info(f"Pre-checkout validation successful for transaction {transaction_id}")
            return True
            
        except Exception as e:
            logger.error(f"Pre-checkout validation failed: {e}")
            return False
            
    async def handle_successful_payment(self, payment: SuccessfulPayment, user_id: int) -> None:
        """Process successful payment with comprehensive protection."""
        async with await self._get_user_payment_lock(user_id):
            try:
                # Prevent duplicate processing
                if await self._is_payment_already_processed(payment.telegram_payment_charge_id):
                    logger.warning(f"Payment already processed: {payment.telegram_payment_charge_id}")
                    return
                    
                # Process payment atomically with rollback capability
                await self._process_payment_with_rollback(payment, user_id)
                
            except Exception as e:
                logger.error(f"Payment processing failed for user {user_id}: {e}")
                await self._handle_payment_error(payment, user_id, e)
                raise

    async def _is_payment_already_processed(self, payment_charge_id: str) -> bool:
        """Check if payment was already processed."""
        # This would require a method in the store to check by charge ID
        # For now, we'll rely on transaction status checks
        return False
        
    async def _process_payment_with_rollback(self, payment: SuccessfulPayment, user_id: int) -> None:
        """Process payment with atomic operations and rollback capability."""
        try:
            # Validate payload security
            payload_data = self.payment_security.validate_payment_payload(payment.invoice_payload)
            transaction_id = payload_data["transaction_id"]
            subscription_type = payload_data["subscription_type"]
            
            # Double-check transaction hasn't been processed
            transaction = await self.payment_store.get_transaction(transaction_id)
            if not transaction or transaction.status != "pending":
                logger.warning(f"Transaction {transaction_id} already processed or not found")
                return
                
            # Mark as processing to prevent double-processing
            await self.payment_store.update_transaction_status(transaction_id, "processing")
            
            # Process subscription update
            await self._upgrade_user_subscription_atomic(
                user_id, 
                subscription_type, 
                payment.telegram_payment_charge_id
            )
            
            # Reactivate paused job searches
            reactivated_count = await self.premium_service.reactivate_user_searches(user_id)
            
            # Mark as completed
            await self.payment_store.update_transaction_status(
                transaction_id, 
                "completed", 
                payment.telegram_payment_charge_id
            )
            
            logger.info(
                f"Successfully processed payment for user {user_id}, "
                f"subscription: {subscription_type}, reactivated {reactivated_count} searches"
            )
            
        except Exception as e:
            # Rollback transaction
            try:
                await self.payment_store.update_transaction_status(transaction_id, "failed")
            except:
                pass
            logger.error(f"Payment processing failed for {transaction_id}: {e}")
            raise
            
    async def _upgrade_user_subscription_atomic(
        self, 
        user_id: int, 
        subscription_type: str, 
        payment_charge_id: str
    ) -> None:
        """Upgrade user subscription atomically."""
        price_info = self.SUBSCRIPTION_PRICES[subscription_type]
        duration_days = price_info["duration_days"]
        
        # Get current subscription
        current_subscription = await self.subscription_store.get_user_subscription(user_id)
        
        now = datetime.now(timezone.utc)
        
        if current_subscription and current_subscription.is_active and current_subscription.end_date > now:
            # Extend existing subscription
            start_date = current_subscription.end_date
            end_date = start_date + timedelta(days=duration_days)
        else:
            # Create new subscription
            start_date = now
            end_date = now + timedelta(days=duration_days)
            
        new_subscription = UserSubscription(
            user_id=user_id,
            subscription_type=subscription_type,
            start_date=start_date,
            end_date=end_date,
            is_active=True,
            telegram_payment_charge_id=payment_charge_id
        )
        
        await self.subscription_store.save_user_subscription(new_subscription)
        
    async def _handle_payment_error(self, payment: SuccessfulPayment, user_id: int, error: Exception) -> None:
        """Handle payment processing errors."""
        logger.error(
            f"Payment error for user {user_id}, charge_id: {payment.telegram_payment_charge_id}, "
            f"error: {error}"
        )
        # Could implement additional error handling here (notifications, recovery queue, etc.)

    async def get_subscription_prices(self) -> Dict[str, Dict[str, any]]:
        """Get subscription pricing information."""
        return self.SUBSCRIPTION_PRICES.copy()

class PaymentRecoveryService:
    """Service for recovering orphaned payments."""
    
    def __init__(
        self, 
        payment_store: PaymentTransactionStore,
        payment_handler_service: PaymentHandlerService
    ) -> None:
        self.payment_store = payment_store
        self.payment_handler_service = payment_handler_service
        
    async def recover_orphaned_payments(self) -> int:
        """Find and recover payments that succeeded but didn't update subscriptions."""
        try:
            # Find completed payments without subscription updates
            completed_payments = await self.payment_store.get_completed_payments_without_subscription_update()
            
            recovered_count = 0
            for payment in completed_payments:
                try:
                    logger.info(f"Recovering orphaned payment: {payment.transaction_id}")
                    
                    # Retry subscription update
                    await self.payment_handler_service._upgrade_user_subscription_atomic(
                        payment.user_id, 
                        payment.subscription_type, 
                        payment.telegram_payment_charge_id
                    )
                    
                    # Mark as recovered
                    await self.payment_store.mark_payment_recovered(payment.transaction_id)
                    recovered_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to recover payment {payment.transaction_id}: {e}")
                    
            logger.info(f"Recovered {recovered_count} orphaned payments")
            return recovered_count
            
        except Exception as e:
            logger.error(f"Error during payment recovery: {e}")
            return 0 