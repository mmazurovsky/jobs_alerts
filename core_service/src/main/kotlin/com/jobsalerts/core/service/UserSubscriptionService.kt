package com.jobsalerts.core.service

import com.jobsalerts.core.domain.model.*
import com.jobsalerts.core.repository.UserSubscriptionRepository
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.stereotype.Service
import java.time.Duration
import java.time.Instant

@Service
class UserSubscriptionService(
    private val userSubscriptionRepository: UserSubscriptionRepository,
    private val userService: UserService
) : Logging {

    /**
     * Get the current subscription tier for a user.
     * If the user has no active paid subscription, returns Free tier.
     * 
     * Note: Free tier is NOT stored in the database - it's the default
     * when no paid subscription exists.
     */
    suspend fun getCurrentSubscriptionTier(telegramUserId: Long): SubscriptionTier {
        val user = userService.getOrCreateUser(telegramUserId)
        val activeSubscription = getActiveSubscription(user.id)
        
        return if (activeSubscription != null) {
            logger.debug { "User ${user.id} has active subscription: ${activeSubscription.subscriptionName}" }
            SubscriptionTier.fromName(activeSubscription.subscriptionName)
        } else {
            logger.debug { "User ${user.id} has no active paid subscription, using FREE tier" }
            SubscriptionTier.getDefault() // Returns FreeSubscriptionTier
        }
    }

    /**
     * Get the currently active subscription for a user.
     * Returns null if the user has no active paid subscription (i.e., they're on Free tier).
     */
    suspend fun getActiveSubscription(userId: String, at: Instant = Instant.now()): UserSubscription? {
        return userSubscriptionRepository.findActiveSubscription(userId, at)
    }

    /**
     * Create a new paid subscription for a user.
     * Automatically cancels any existing active subscription to ensure only one is active.
     * 
     * Note: This method is for PAID subscriptions only. Free tier users do not get
     * a subscription record - they get Free tier by having no active subscription.
     */
    suspend fun createSubscription(
        telegramUserId: Long,
        subscriptionTier: SubscriptionTier,
        startTime: Instant = Instant.now()
    ): UserSubscription {
        require(subscriptionTier.name != "FREE") { 
            "Free subscriptions are not stored in database. Free tier is the default." 
        }
        
        val user = userService.getOrCreateUser(telegramUserId)
        
        // Cancel any existing active subscription to ensure only one is active
        cancelActiveSubscription(user.id)
        
        val subscription = UserSubscription(
            id = "${user.id}-${subscriptionTier.name}-${startTime.epochSecond}",
            userId = user.id,
            subscriptionName = subscriptionTier.name,
            activeFrom = startTime,
            activeTo = startTime.plus(subscriptionTier.duration),
            createdAt = Instant.now()
        )
        
        val savedSubscription = userSubscriptionRepository.save(subscription)
        logger.info { "Created ${subscriptionTier.name} subscription for user ${user.id}" }
        return savedSubscription
    }

    /**
     * Cancel the currently active subscription for a user.
     * After cancellation, the user will fall back to Free tier.
     */
    suspend fun cancelActiveSubscription(userId: String) {
        val activeSubscription = getActiveSubscription(userId)
        if (activeSubscription != null) {
            val cancelledSubscription = activeSubscription.copy(isCancelled = true)
            userSubscriptionRepository.save(cancelledSubscription)
            logger.info { "Cancelled subscription ${activeSubscription.id} for user $userId" }
        }
    }

    /**
     * Extend an existing subscription by adding additional duration.
     * Returns null if no active subscription exists.
     */
    suspend fun extendSubscription(
        telegramUserId: Long,
        additionalDuration: Duration
    ): UserSubscription? {
        val user = userService.getOrCreateUser(telegramUserId)
        val activeSubscription = getActiveSubscription(user.id)
        
        return if (activeSubscription != null) {
            val extendedSubscription = activeSubscription.copy(
                activeTo = activeSubscription.activeTo.plus(additionalDuration)
            )
            val savedSubscription = userSubscriptionRepository.save(extendedSubscription)
            logger.info { "Extended subscription ${activeSubscription.id} by $additionalDuration" }
            savedSubscription
        } else {
            logger.warn { "Attempted to extend subscription for user ${user.id} but no active subscription found" }
            null
        }
    }

    /**
     * Check if a user has any active paid subscription.
     * Returns false for Free tier users (who have no subscription record).
     */
    suspend fun hasActiveSubscription(telegramUserId: Long): Boolean {
        val user = userService.getUserByTelegramId(telegramUserId) ?: return false
        return getActiveSubscription(user.id) != null
    }
}