package com.jobsalerts.core.service

import com.jobsalerts.core.domain.model.*
import org.assertj.core.api.Assertions.*
import org.junit.jupiter.api.Test

/**
 * Simple test to verify Free tier limits without complex mocking.
 */
class UserLimitsSimpleTest {

    @Test
    fun `Free tier should have correct limits`() {
        // Given: Free subscription tier
        val freeTier = FreeSubscriptionTier

        // Then: Should have expected limits
        assertThat(freeTier.name).isEqualTo("FREE")
        assertThat(freeTier.displayName).isEqualTo("Free")
        assertThat(freeTier.maxJobAlerts).isEqualTo(5)
        assertThat(freeTier.maxDailySearches).isEqualTo(3)
        assertThat(freeTier.features).contains(
            SubscriptionFeature.BASIC_ALERTS,
            SubscriptionFeature.INSTANT_SEARCH
        )
    }

    @Test
    fun `Premium tier should have higher limits`() {
        // Given: Premium subscription tier
        val premiumTier = PremiumSubscriptionTier

        // Then: Should have expected limits
        assertThat(premiumTier.name).isEqualTo("PREMIUM")
        assertThat(premiumTier.displayName).isEqualTo("Premium")
        assertThat(premiumTier.maxJobAlerts).isEqualTo(25)
        assertThat(premiumTier.maxDailySearches).isEqualTo(15)
        assertThat(premiumTier.features).contains(
            SubscriptionFeature.BASIC_ALERTS,
            SubscriptionFeature.INSTANT_SEARCH,
            SubscriptionFeature.ADVANCED_FILTERS
        )
    }

    @Test
    fun `SubscriptionTier fromName should work correctly`() {
        // When/Then: Getting tier by name
        assertThat(SubscriptionTier.fromName("FREE")).isEqualTo(FreeSubscriptionTier)
        assertThat(SubscriptionTier.fromName("PREMIUM")).isEqualTo(PremiumSubscriptionTier)
        assertThat(SubscriptionTier.fromName("UNKNOWN")).isEqualTo(FreeSubscriptionTier)
    }

    @Test
    fun `SubscriptionTier getDefault should return Free tier`() {
        // When: Getting default tier
        val tier = SubscriptionTier.getDefault()

        // Then: Should return Free tier
        assertThat(tier).isEqualTo(FreeSubscriptionTier)
    }

    @Test
    fun `UserSubscription isActive should work correctly`() {
        val now = java.time.Instant.now()
        
        // Given: Active subscription
        val activeSubscription = UserSubscription(
            id = "sub-123",
            userId = "user-123",
            subscriptionName = "PREMIUM",
            activeFrom = now.minus(1, java.time.temporal.ChronoUnit.DAYS),
            activeTo = now.plus(29, java.time.temporal.ChronoUnit.DAYS),
            createdAt = now,
            isCancelled = false
        )

        // Then: Should be active
        assertThat(activeSubscription.isActive(now)).isTrue()

        // Given: Cancelled subscription
        val cancelledSubscription = activeSubscription.copy(isCancelled = true)

        // Then: Should not be active
        assertThat(cancelledSubscription.isActive(now)).isFalse()

        // Given: Expired subscription
        val expiredSubscription = UserSubscription(
            id = "sub-456",
            userId = "user-123",
            subscriptionName = "PREMIUM",
            activeFrom = now.minus(31, java.time.temporal.ChronoUnit.DAYS),
            activeTo = now.minus(1, java.time.temporal.ChronoUnit.DAYS),
            createdAt = now.minus(31, java.time.temporal.ChronoUnit.DAYS),
            isCancelled = false
        )

        // Then: Should not be active
        assertThat(expiredSubscription.isActive(now)).isFalse()
    }

    @Test
    fun `LimitCheckResult should work correctly`() {
        // Given: Limit check result
        val result = LimitCheckResult(
            allowed = false,
            reason = "Test reason",
            currentUsage = 5,
            maxAllowed = 5,
            subscriptionTier = FreeSubscriptionTier
        )

        // Then: Should have correct properties
        assertThat(result.allowed).isFalse()
        assertThat(result.reason).isEqualTo("Test reason")
        assertThat(result.currentUsage).isEqualTo(5)
        assertThat(result.maxAllowed).isEqualTo(5)
        assertThat(result.subscriptionTier).isEqualTo(FreeSubscriptionTier)
    }
}