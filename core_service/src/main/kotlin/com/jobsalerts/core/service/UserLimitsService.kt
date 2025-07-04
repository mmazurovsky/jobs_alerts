package com.jobsalerts.core.service

import com.jobsalerts.core.domain.model.*
import com.jobsalerts.core.repository.UserUsageRepository
import com.jobsalerts.core.repository.JobSearchRepository
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.stereotype.Service
import java.time.LocalDate

@Service
class UserLimitsService(
    private val userService: UserService,
    private val userSubscriptionService: UserSubscriptionService,
    private val userUsageRepository: UserUsageRepository,
    private val jobSearchRepository: JobSearchRepository
) : Logging {

    /**
     * Check if a user can create a new job alert based on their subscription tier.
     * Free tier: max 5 alerts
     * Premium and above: higher limits (to be implemented)
     */
    suspend fun checkJobAlertLimit(telegramUserId: Long): LimitCheckResult {
        val currentTier = userSubscriptionService.getCurrentSubscriptionTier(telegramUserId)
        val currentAlerts = jobSearchRepository.countByUserId(telegramUserId)
        val maxAllowed = currentTier.maxJobAlerts
        
        logger.debug { "Checking job alert limit for user $telegramUserId: $currentAlerts/$maxAllowed (${currentTier.displayName})" }
        
        return when {
            maxAllowed == -1 -> {
                // Unlimited alerts (Enterprise tier)
                LimitCheckResult(
                    allowed = true, 
                    subscriptionTier = currentTier,
                    currentUsage = currentAlerts.toInt(),
                    maxAllowed = maxAllowed
                )
            }
            currentAlerts < maxAllowed -> {
                // Within limits
                LimitCheckResult(
                    allowed = true, 
                    currentUsage = currentAlerts.toInt(), 
                    maxAllowed = maxAllowed,
                    subscriptionTier = currentTier
                )
            }
            else -> {
                // At or over limit
                val reason = when (currentTier.name) {
                    "FREE" -> "You've reached your limit of $maxAllowed job alerts on the Free plan. Delete some alerts or upgrade to Premium for more!"
                    else -> "You've reached your limit of $maxAllowed job alerts. Consider upgrading for higher limits!"
                }
                
                LimitCheckResult(
                    allowed = false,
                    reason = reason,
                    currentUsage = currentAlerts.toInt(),
                    maxAllowed = maxAllowed,
                    subscriptionTier = currentTier
                )
            }
        }
    }

    /**
     * Check if a user can perform an instant search based on their daily limits.
     * Free tier: max 3 searches per day
     * Premium and above: higher limits (to be implemented)
     */
    suspend fun checkDailySearchLimit(telegramUserId: Long): LimitCheckResult {
        val currentTier = userSubscriptionService.getCurrentSubscriptionTier(telegramUserId)
        val user = userService.getOrCreateUser(telegramUserId)
        val today = LocalDate.now()
        val dateStr = today.toString()
        
        val todayUsage = userUsageRepository.findByUserIdAndDate(user.id, dateStr)
        val currentSearches = todayUsage?.instantSearchesCount ?: 0
        val maxAllowed = currentTier.maxDailySearches
        
        logger.debug { "Checking daily search limit for user $telegramUserId: $currentSearches/$maxAllowed (${currentTier.displayName})" }
        
        return when {
            maxAllowed == -1 -> {
                // Unlimited searches (Enterprise tier)
                LimitCheckResult(
                    allowed = true, 
                    subscriptionTier = currentTier,
                    currentUsage = currentSearches,
                    maxAllowed = maxAllowed
                )
            }
            currentSearches < maxAllowed -> {
                // Within limits
                LimitCheckResult(
                    allowed = true,
                    currentUsage = currentSearches,
                    maxAllowed = maxAllowed,
                    subscriptionTier = currentTier
                )
            }
            else -> {
                // At or over limit
                val reason = when (currentTier.name) {
                    "FREE" -> "You've used all $maxAllowed daily searches on the Free plan. Try again tomorrow or upgrade to Premium for more searches!"
                    else -> "You've reached your daily limit of $maxAllowed searches. Try again tomorrow or upgrade for higher limits!"
                }
                
                LimitCheckResult(
                    allowed = false,
                    reason = reason,
                    currentUsage = currentSearches,
                    maxAllowed = maxAllowed,
                    subscriptionTier = currentTier
                )
            }
        }
    }

    /**
     * Track that a user has performed an instant search.
     * This increments their daily search count for rate limiting.
     */
    suspend fun trackDailySearch(telegramUserId: Long) {
        val user = userService.getOrCreateUser(telegramUserId)
        val today = LocalDate.now()
        
        logger.debug { "Tracking daily search for user $telegramUserId on $today" }
        userUsageRepository.incrementDailySearches(user.id, today)
    }

    /**
     * Get current usage statistics for a user.
     * Useful for showing users their current limits and usage.
     */
    suspend fun getCurrentUsage(telegramUserId: Long): UserUsageStats {
        val currentTier = userSubscriptionService.getCurrentSubscriptionTier(telegramUserId)
        val user = userService.getOrCreateUser(telegramUserId)
        val today = LocalDate.now()
        val dateStr = today.toString()
        
        val todayUsage = userUsageRepository.findByUserIdAndDate(user.id, dateStr)
        val currentSearches = todayUsage?.instantSearchesCount ?: 0
        val currentAlerts = jobSearchRepository.countByUserId(telegramUserId)
        
        return UserUsageStats(
            subscriptionTier = currentTier,
            currentJobAlerts = currentAlerts.toInt(),
            maxJobAlerts = currentTier.maxJobAlerts,
            currentDailySearches = currentSearches,
            maxDailySearches = currentTier.maxDailySearches,
            date = today
        )
    }
}

/**
 * Data class representing a user's current usage statistics.
 */
data class UserUsageStats(
    val subscriptionTier: SubscriptionTier,
    val currentJobAlerts: Int,
    val maxJobAlerts: Int,
    val currentDailySearches: Int,
    val maxDailySearches: Int,
    val date: LocalDate
)