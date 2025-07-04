package com.jobsalerts.core.service

import com.jobsalerts.core.domain.model.*
import com.jobsalerts.core.repository.UserSubscriptionRepository
import kotlinx.coroutines.runBlocking
import org.assertj.core.api.Assertions.*
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.extension.ExtendWith
import org.mockito.Mock
import org.mockito.junit.jupiter.MockitoExtension
import org.mockito.kotlin.*
import org.mockito.Mockito.lenient
import java.time.Instant
import java.time.temporal.ChronoUnit

@ExtendWith(MockitoExtension::class)
class UserSubscriptionServiceTest {

    @Mock
    private lateinit var userSubscriptionRepository: UserSubscriptionRepository

    @Mock
    private lateinit var userService: UserService

    private lateinit var userSubscriptionService: UserSubscriptionService

    private val testUserId = 12345L
    private val testUser = User(
        id = "user-12345",
        telegramUserId = testUserId,
        username = "testuser",
        createdAt = Instant.now(),
        lastActiveAt = Instant.now()
    )

    @BeforeEach
    fun setUp() {
        userSubscriptionService = UserSubscriptionService(
            userSubscriptionRepository = userSubscriptionRepository,
            userService = userService
        )

        runBlocking {
            lenient().whenever(userService.getOrCreateUser(testUserId)).thenReturn(testUser)
        }
    }

    @Test
    fun `getCurrentSubscriptionTier should return Free tier when user has no active subscription`() = runBlocking {
        // Given: User has no active subscription
        whenever(userSubscriptionRepository.findActiveSubscription(eq(testUser.id), any())).thenReturn(null)

        // When: Getting current subscription tier
        val tier = userSubscriptionService.getCurrentSubscriptionTier(testUserId)

        // Then: Should return Free tier
        assertThat(tier).isEqualTo(FreeSubscriptionTier)
        assertThat(tier.name).isEqualTo("FREE")
        assertThat(tier.maxJobAlerts).isEqualTo(5)
        assertThat(tier.maxDailySearches).isEqualTo(3)
    }

    @Test
    fun `getCurrentSubscriptionTier should return Premium tier when user has active premium subscription`() = runBlocking {
        // Given: User has active Premium subscription
        val premiumSubscription = UserSubscription(
            id = "sub-premium-123",
            userId = testUser.id,
            subscriptionName = "PREMIUM",
            activeFrom = Instant.now().minus(1, ChronoUnit.DAYS),
            activeTo = Instant.now().plus(29, ChronoUnit.DAYS),
            createdAt = Instant.now(),
            isCancelled = false
        )
        whenever(userSubscriptionRepository.findActiveSubscription(testUser.id, any())).thenReturn(premiumSubscription)

        // When: Getting current subscription tier
        val tier = userSubscriptionService.getCurrentSubscriptionTier(testUserId)

        // Then: Should return Premium tier
        assertThat(tier).isEqualTo(PremiumSubscriptionTier)
        assertThat(tier.name).isEqualTo("PREMIUM")
        assertThat(tier.maxJobAlerts).isEqualTo(25)
        assertThat(tier.maxDailySearches).isEqualTo(15)
    }

    @Test
    fun `getActiveSubscription should return null when user has no active subscription`() = runBlocking {
        // Given: User has no active subscription
        whenever(userSubscriptionRepository.findActiveSubscription(eq(testUser.id), any())).thenReturn(null)

        // When: Getting active subscription
        val subscription = userSubscriptionService.getActiveSubscription(testUser.id)

        // Then: Should return null
        assertThat(subscription).isNull()
    }

    @Test
    fun `getActiveSubscription should return subscription when user has active subscription`() = runBlocking {
        // Given: User has active subscription
        val activeSubscription = UserSubscription(
            id = "sub-premium-123",
            userId = testUser.id,
            subscriptionName = "PREMIUM",
            activeFrom = Instant.now().minus(1, ChronoUnit.DAYS),
            activeTo = Instant.now().plus(29, ChronoUnit.DAYS),
            createdAt = Instant.now(),
            isCancelled = false
        )
        whenever(userSubscriptionRepository.findActiveSubscription(eq(testUser.id), any())).thenReturn(activeSubscription)

        // When: Getting active subscription
        val subscription = userSubscriptionService.getActiveSubscription(testUser.id)

        // Then: Should return the subscription
        assertThat(subscription).isNotNull()
        assertThat(subscription!!.subscriptionName).isEqualTo("PREMIUM")
        assertThat(subscription.isCancelled).isFalse()
    }

    @Test
    fun `createSubscription should throw exception when trying to create FREE subscription`() = runBlocking {
        // When/Then: Attempting to create FREE subscription should throw exception
        assertThatThrownBy {
            runBlocking {
                userSubscriptionService.createSubscription(testUserId, FreeSubscriptionTier)
            }
        }.isInstanceOf(IllegalArgumentException::class.java)
            .hasMessageContaining("Free subscriptions are not stored in database")
    }

    @Test
    fun `createSubscription should create Premium subscription and cancel existing ones`() = runBlocking {
        // Given: User has existing active subscription
        val existingSubscription = UserSubscription(
            id = "old-sub-123",
            userId = testUser.id,
            subscriptionName = "PREMIUM",
            activeFrom = Instant.now().minus(10, ChronoUnit.DAYS),
            activeTo = Instant.now().plus(20, ChronoUnit.DAYS),
            createdAt = Instant.now(),
            isCancelled = false
        )
        whenever(userSubscriptionRepository.findActiveSubscription(testUser.id, any())).thenReturn(existingSubscription)
        
        val newSubscription = UserSubscription(
            id = "new-sub-456",
            userId = testUser.id,
            subscriptionName = "PREMIUM",
            activeFrom = Instant.now(),
            activeTo = Instant.now().plus(30, ChronoUnit.DAYS),
            createdAt = Instant.now(),
            isCancelled = false
        )
        whenever(userSubscriptionRepository.save(any())).thenReturn(newSubscription)

        // When: Creating new subscription
        val result = userSubscriptionService.createSubscription(testUserId, PremiumSubscriptionTier)

        // Then: Should cancel existing subscription and create new one
        verify(userSubscriptionRepository).save(existingSubscription.copy(isCancelled = true))
        verify(userSubscriptionRepository).save(argThat { subscription ->
            subscription.userId == testUser.id &&
            subscription.subscriptionName == "PREMIUM" &&
            !subscription.isCancelled
        })
        assertThat(result.subscriptionName).isEqualTo("PREMIUM")
        assertThat(result.isCancelled).isFalse()
    }

    @Test
    fun `hasActiveSubscription should return false when user has no subscription`() = runBlocking {
        // Given: User has no active subscription
        whenever(userSubscriptionRepository.findActiveSubscription(eq(testUser.id), any())).thenReturn(null)

        // When: Checking if user has active subscription
        val hasSubscription = userSubscriptionService.hasActiveSubscription(testUserId)

        // Then: Should return false
        assertThat(hasSubscription).isFalse()
    }

    @Test
    fun `hasActiveSubscription should return true when user has active subscription`() = runBlocking {
        // Given: User has active subscription
        val activeSubscription = UserSubscription(
            id = "sub-premium-123",
            userId = testUser.id,
            subscriptionName = "PREMIUM",
            activeFrom = Instant.now().minus(1, ChronoUnit.DAYS),
            activeTo = Instant.now().plus(29, ChronoUnit.DAYS),
            createdAt = Instant.now(),
            isCancelled = false
        )
        whenever(userSubscriptionRepository.findActiveSubscription(eq(testUser.id), any())).thenReturn(activeSubscription)

        // When: Checking if user has active subscription
        val hasSubscription = userSubscriptionService.hasActiveSubscription(testUserId)

        // Then: Should return true
        assertThat(hasSubscription).isTrue()
    }

    @Test
    fun `hasActiveSubscription should return false when user doesn't exist`() = runBlocking {
        // Given: User doesn't exist
        whenever(userService.getUserByTelegramId(testUserId)).thenReturn(null)

        // When: Checking if user has active subscription
        val hasSubscription = userSubscriptionService.hasActiveSubscription(testUserId)

        // Then: Should return false
        assertThat(hasSubscription).isFalse()
    }

    @Test
    fun `UserSubscription isActive should return true for valid active subscription`() {
        // Given: Subscription that is currently active
        val now = Instant.now()
        val subscription = UserSubscription(
            id = "sub-123",
            userId = "user-123",
            subscriptionName = "PREMIUM",
            activeFrom = now.minus(1, ChronoUnit.DAYS),
            activeTo = now.plus(29, ChronoUnit.DAYS),
            createdAt = now,
            isCancelled = false
        )

        // When: Checking if subscription is active
        val isActive = subscription.isActive(now)

        // Then: Should be active
        assertThat(isActive).isTrue()
    }

    @Test
    fun `UserSubscription isActive should return false for cancelled subscription`() {
        // Given: Cancelled subscription
        val now = Instant.now()
        val subscription = UserSubscription(
            id = "sub-123",
            userId = "user-123",
            subscriptionName = "PREMIUM",
            activeFrom = now.minus(1, ChronoUnit.DAYS),
            activeTo = now.plus(29, ChronoUnit.DAYS),
            createdAt = now,
            isCancelled = true
        )

        // When: Checking if subscription is active
        val isActive = subscription.isActive(now)

        // Then: Should not be active
        assertThat(isActive).isFalse()
    }

    @Test
    fun `UserSubscription isActive should return false for expired subscription`() {
        // Given: Expired subscription
        val now = Instant.now()
        val subscription = UserSubscription(
            id = "sub-123",
            userId = "user-123",
            subscriptionName = "PREMIUM",
            activeFrom = now.minus(31, ChronoUnit.DAYS),
            activeTo = now.minus(1, ChronoUnit.DAYS),
            createdAt = now.minus(31, ChronoUnit.DAYS),
            isCancelled = false
        )

        // When: Checking if subscription is active
        val isActive = subscription.isActive(now)

        // Then: Should not be active
        assertThat(isActive).isFalse()
    }

    @Test
    fun `UserSubscription isActive should return false for future subscription`() {
        // Given: Future subscription (not yet started)
        val now = Instant.now()
        val subscription = UserSubscription(
            id = "sub-123",
            userId = "user-123",
            subscriptionName = "PREMIUM",
            activeFrom = now.plus(1, ChronoUnit.DAYS),
            activeTo = now.plus(31, ChronoUnit.DAYS),
            createdAt = now,
            isCancelled = false
        )

        // When: Checking if subscription is active
        val isActive = subscription.isActive(now)

        // Then: Should not be active yet
        assertThat(isActive).isFalse()
    }
}