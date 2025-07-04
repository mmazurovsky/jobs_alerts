package com.jobsalerts.core.domain.model

import org.springframework.data.annotation.Id
import org.springframework.data.mongodb.core.mapping.Document
import org.springframework.data.mongodb.core.mapping.Field
import java.time.Duration
import java.time.Instant

/**
 * Interface for subscription tiers with different limits and features.
 * Similar to TimePeriod pattern - interface with specific implementations.
 */
interface SubscriptionTier {
    val name: String
    val displayName: String
    val maxJobAlerts: Int
    val maxDailySearches: Int
    val duration: Duration
    val features: Set<SubscriptionFeature>
    
    companion object {
        fun fromName(name: String): SubscriptionTier = when (name.uppercase()) {
            "FREE" -> FreeSubscriptionTier
            "PREMIUM" -> PremiumSubscriptionTier
            else -> FreeSubscriptionTier
        }
        
        fun getDefault(): SubscriptionTier = FreeSubscriptionTier
    }
}

/**
 * Free tier implementation - default when no paid subscription exists.
 * Note: Free subscriptions are NOT stored in the database collection.
 */
object FreeSubscriptionTier : SubscriptionTier {
    override val name = "FREE"
    override val displayName = "Free"
    override val maxJobAlerts = 5
    override val maxDailySearches = 3
    override val duration: Duration = Duration.ofDays(365) // Always available
    override val features = setOf(
        SubscriptionFeature.BASIC_ALERTS,
        SubscriptionFeature.INSTANT_SEARCH
    )
}

/**
 * Premium tier implementation - placeholder for future implementation.
 * This will be fleshed out when premium subscriptions are added.
 */
object PremiumSubscriptionTier : SubscriptionTier {
    override val name = "PREMIUM"
    override val displayName = "Premium"
    override val maxJobAlerts = 25
    override val maxDailySearches = 15
    override val duration: Duration = Duration.ofDays(30) // Monthly
    override val features = setOf(
        SubscriptionFeature.BASIC_ALERTS,
        SubscriptionFeature.INSTANT_SEARCH,
        SubscriptionFeature.ADVANCED_FILTERS
    )
}

/**
 * Feature flags for different subscription capabilities.
 * Used for controlling access to specific features.
 */
enum class SubscriptionFeature {
    BASIC_ALERTS,
    INSTANT_SEARCH,
    ADVANCED_FILTERS,
    PRIORITY_SUPPORT,
    API_ACCESS
}

/**
 * User subscription entity - only for PAID subscriptions.
 * Free tier users will NOT have entries in this collection.
 * One-to-many relationship with User, but only one active subscription at a time.
 */
@Document(collection = "user_subscriptions")
data class UserSubscription(
    @Id val id: String,
    @field:Field("user_id") val userId: String,
    @field:Field("subscription_name") val subscriptionName: String, // "PREMIUM", "ENTERPRISE", etc. (NOT "FREE")
    @field:Field("active_from") val activeFrom: Instant,
    @field:Field("active_to") val activeTo: Instant,
    @field:Field("created_at") val createdAt: Instant,
    @field:Field("is_cancelled") val isCancelled: Boolean = false
) {
    /**
     * Checks if this subscription is currently active.
     * A subscription is active if:
     * 1. Not cancelled
     * 2. Current time is after activeFrom
     * 3. Current time is before activeTo
     */
    fun isActive(at: Instant = Instant.now()): Boolean {
        return !isCancelled && !at.isBefore(activeFrom) && at.isBefore(activeTo)
    }
}

/**
 * User entity - basic user information without subscription details.
 * Subscription information is stored separately in UserSubscription collection.
 */
@Document(collection = "users")
data class User(
    @Id val id: String,
    @field:Field("telegram_user_id") val telegramUserId: Long,
    @field:Field("username") val username: String?,
    @field:Field("created_at") val createdAt: Instant,
    @field:Field("last_active_at") val lastActiveAt: Instant
)

/**
 * Daily usage tracking for rate-limited features like instant searches.
 * Tracks usage per user per day for enforcement of daily limits.
 */
@Document(collection = "user_usage")
data class UserUsage(
    @Id val id: String,
    @field:Field("user_id") val userId: String,
    @field:Field("date") val date: String, // Format: YYYY-MM-DD for easy querying
    @field:Field("instant_searches_count") val instantSearchesCount: Int = 0,
    @field:Field("created_at") val createdAt: Instant
)

/**
 * Result of checking user limits for a specific action.
 * Contains all information needed to inform the user about their limits.
 */
data class LimitCheckResult(
    val allowed: Boolean,
    val reason: String? = null,
    val currentUsage: Int = 0,
    val maxAllowed: Int = 0,
    val subscriptionTier: SubscriptionTier
)