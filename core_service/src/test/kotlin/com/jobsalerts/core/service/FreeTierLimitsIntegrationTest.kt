package com.jobsalerts.core.service

import com.jobsalerts.core.domain.model.*
import com.jobsalerts.core.repository.JobSearchRepository
import com.jobsalerts.core.repository.UserRepository
import com.jobsalerts.core.repository.UserSubscriptionRepository
import com.jobsalerts.core.repository.UserUsageRepository
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
import java.time.LocalDate

/**
 * Integration test that verifies Free tier limits are properly enforced
 * across the entire user limits system.
 */
@ExtendWith(MockitoExtension::class)
class FreeTierLimitsIntegrationTest {

    @Mock
    private lateinit var userRepository: UserRepository

    @Mock
    private lateinit var userSubscriptionRepository: UserSubscriptionRepository

    @Mock
    private lateinit var userUsageRepository: UserUsageRepository

    @Mock
    private lateinit var jobSearchRepository: JobSearchRepository

    private lateinit var userService: UserService
    private lateinit var userSubscriptionService: UserSubscriptionService
    private lateinit var userLimitsService: UserLimitsService

    private val testUserId = 98765L
    private val testUser = User(
        id = "user-98765",
        telegramUserId = testUserId,
        username = "freetieruser",
        createdAt = Instant.now(),
        lastActiveAt = Instant.now()
    )

    @BeforeEach
    fun setUp() {
        // Create the service hierarchy
        userService = UserService(userRepository)
        userSubscriptionService = UserSubscriptionService(userSubscriptionRepository, userService)
        userLimitsService = UserLimitsService(
            userService = userService,
            userSubscriptionService = userSubscriptionService,
            userUsageRepository = userUsageRepository,
            jobSearchRepository = jobSearchRepository
        )

        // Setup common mocks - using lenient to avoid UnnecessaryStubbingException
        runBlocking {
            lenient().whenever(userRepository.findByTelegramUserId(testUserId)).thenReturn(testUser)
            lenient().whenever(userRepository.save(any())).thenReturn(testUser)
            
            // User has no paid subscription - so they get Free tier
            lenient().whenever(userSubscriptionRepository.findActiveSubscription(eq(testUser.id), any())).thenReturn(null)
        }
    }

    @Test
    fun `Free tier user should be allowed to create alerts 1 through 5 but denied on 6th`() = runBlocking {
        // Test creating alerts 1-5 (should all be allowed)
        for (alertCount in 1..5) {
            // Given: User has (alertCount - 1) existing alerts
            whenever(jobSearchRepository.countByUserId(testUserId)).thenReturn((alertCount - 1).toLong())

            // When: Checking if user can create another alert
            val result = userLimitsService.checkJobAlertLimit(testUserId)

            // Then: Should be allowed
            assertThat(result.allowed).isTrue()
            assertThat(result.currentUsage).isEqualTo(alertCount - 1)
            assertThat(result.maxAllowed).isEqualTo(5)
            assertThat(result.subscriptionTier.name).isEqualTo("FREE")
        }

        // Test creating 6th alert (should be denied)
        whenever(jobSearchRepository.countByUserId(testUserId)).thenReturn(5L)

        val result = userLimitsService.checkJobAlertLimit(testUserId)

        assertThat(result.allowed).isFalse()
        assertThat(result.currentUsage).isEqualTo(5)
        assertThat(result.maxAllowed).isEqualTo(5)
        assertThat(result.reason).contains("You've reached your limit of 5 job alerts on the Free plan")
    }

    @Test
    fun `Free tier user should be allowed 1-3 daily searches but denied on 4th`() = runBlocking {
        val today = LocalDate.now()
        val todayStr = today.toString()

        // Test searches 1-3 (should all be allowed)
        for (searchCount in 1..3) {
            // Given: User has (searchCount - 1) searches today
            val todayUsage = if (searchCount == 1) {
                null // No usage record yet
            } else {
                UserUsage(
                    id = "${testUser.id}-$todayStr",
                    userId = testUser.id,
                    date = todayStr,
                    instantSearchesCount = searchCount - 1,
                    createdAt = Instant.now()
                )
            }
            whenever(userUsageRepository.findByUserIdAndDate(eq(testUser.id), eq(todayStr))).thenReturn(todayUsage)

            // When: Checking if user can perform another search
            val result = userLimitsService.checkDailySearchLimit(testUserId)

            // Then: Should be allowed
            assertThat(result.allowed).isTrue()
            assertThat(result.currentUsage).isEqualTo(if (searchCount == 1) 0 else searchCount - 1)
            assertThat(result.maxAllowed).isEqualTo(3)
            assertThat(result.subscriptionTier.name).isEqualTo("FREE")
        }

        // Test 4th search (should be denied)
        val maxUsage = UserUsage(
            id = "${testUser.id}-$todayStr",
            userId = testUser.id,
            date = todayStr,
            instantSearchesCount = 3,
            createdAt = Instant.now()
        )
        whenever(userUsageRepository.findByUserIdAndDate(eq(testUser.id), eq(todayStr))).thenReturn(maxUsage)

        val result = userLimitsService.checkDailySearchLimit(testUserId)

        assertThat(result.allowed).isFalse()
        assertThat(result.currentUsage).isEqualTo(3)
        assertThat(result.maxAllowed).isEqualTo(3)
        assertThat(result.reason).contains("You've used all 3 daily searches on the Free plan")
    }

    @Test
    fun `trackDailySearch should properly increment usage for Free tier user`() = runBlocking {
        val today = LocalDate.now()

        // When: Tracking a daily search
        userLimitsService.trackDailySearch(testUserId)

        // Then: Should call increment with correct parameters
        verify(userUsageRepository).incrementDailySearches(eq(testUser.id), eq(today))
    }

    @Test
    fun `getCurrentUsage should return correct Free tier statistics`() = runBlocking {
        // Given: User has some alerts and searches
        val today = LocalDate.now()
        val todayUsage = UserUsage(
            id = "${testUser.id}-$today",
            userId = testUser.id,
            date = today.toString(),
            instantSearchesCount = 2,
            createdAt = Instant.now()
        )
        whenever(jobSearchRepository.countByUserId(testUserId)).thenReturn(4L)
        whenever(userUsageRepository.findByUserIdAndDate(eq(testUser.id), eq(today.toString()))).thenReturn(todayUsage)

        // When: Getting current usage
        val usage = userLimitsService.getCurrentUsage(testUserId)

        // Then: Should return correct Free tier limits and usage
        assertThat(usage.subscriptionTier.name).isEqualTo("FREE")
        assertThat(usage.subscriptionTier.displayName).isEqualTo("Free")
        assertThat(usage.currentJobAlerts).isEqualTo(4)
        assertThat(usage.maxJobAlerts).isEqualTo(5)
        assertThat(usage.currentDailySearches).isEqualTo(2)
        assertThat(usage.maxDailySearches).isEqualTo(3)
        assertThat(usage.date).isEqualTo(today)
    }

    @Test
    fun `Free tier user without any subscriptions should get correct tier from service chain`() = runBlocking {
        // Given: User exists but has no paid subscriptions (typical Free tier user)
        whenever(userSubscriptionRepository.findActiveSubscription(eq(testUser.id), any())).thenReturn(null)

        // When: Getting subscription tier through the service chain
        val tier = userSubscriptionService.getCurrentSubscriptionTier(testUserId)

        // Then: Should get Free tier
        assertThat(tier).isEqualTo(FreeSubscriptionTier)
        assertThat(tier.name).isEqualTo("FREE")
        assertThat(tier.displayName).isEqualTo("Free")
        assertThat(tier.maxJobAlerts).isEqualTo(5)
        assertThat(tier.maxDailySearches).isEqualTo(3)
        assertThat(tier.features).containsExactlyInAnyOrder(
            SubscriptionFeature.BASIC_ALERTS,
            SubscriptionFeature.INSTANT_SEARCH
        )
    }

    @Test
    fun `New Free tier user should be able to create their first alert and perform first search`() = runBlocking {
        // Given: Brand new user with no alerts or searches
        whenever(jobSearchRepository.countByUserId(testUserId)).thenReturn(0L)
        whenever(userUsageRepository.findByUserIdAndDate(eq(testUser.id), eq(LocalDate.now().toString()))).thenReturn(null)

        // When: Checking limits for first alert
        val alertResult = userLimitsService.checkJobAlertLimit(testUserId)

        // Then: Should be allowed
        assertThat(alertResult.allowed).isTrue()
        assertThat(alertResult.currentUsage).isEqualTo(0)
        assertThat(alertResult.maxAllowed).isEqualTo(5)

        // When: Checking limits for first search
        val searchResult = userLimitsService.checkDailySearchLimit(testUserId)

        // Then: Should be allowed
        assertThat(searchResult.allowed).isTrue()
        assertThat(searchResult.currentUsage).isEqualTo(0)
        assertThat(searchResult.maxAllowed).isEqualTo(3)
    }

    @Test
    fun `User at Free tier limits should get helpful error messages`() = runBlocking {
        // Given: User at job alert limit
        whenever(jobSearchRepository.countByUserId(testUserId)).thenReturn(5L)

        // When: Checking job alert limit
        val alertResult = userLimitsService.checkJobAlertLimit(testUserId)

        // Then: Should get helpful Free tier message
        assertThat(alertResult.allowed).isFalse()
        assertThat(alertResult.reason).contains("Free plan")
        assertThat(alertResult.reason).contains("Delete some alerts or upgrade to Premium")

        // Given: User at daily search limit
        val today = LocalDate.now()
        val maxUsage = UserUsage(
            id = "${testUser.id}-$today",
            userId = testUser.id,
            date = today.toString(),
            instantSearchesCount = 3,
            createdAt = Instant.now()
        )
        whenever(userUsageRepository.findByUserIdAndDate(eq(testUser.id), eq(today.toString()))).thenReturn(maxUsage)

        // When: Checking daily search limit
        val searchResult = userLimitsService.checkDailySearchLimit(testUserId)

        // Then: Should get helpful Free tier message
        assertThat(searchResult.allowed).isFalse()
        assertThat(searchResult.reason).contains("Free plan")
        assertThat(searchResult.reason).contains("Try again tomorrow or upgrade to Premium")
    }

    @Test
    fun `Free tier should be the default when SubscriptionTier methods are called`() {
        // When: Getting default tier
        val defaultTier = SubscriptionTier.getDefault()

        // Then: Should be Free tier
        assertThat(defaultTier).isEqualTo(FreeSubscriptionTier)

        // When: Getting tier by name for unknown subscription
        val unknownTier = SubscriptionTier.fromName("UNKNOWN")

        // Then: Should fallback to Free tier
        assertThat(unknownTier).isEqualTo(FreeSubscriptionTier)

        // When: Getting Free tier explicitly
        val freeTier = SubscriptionTier.fromName("FREE")

        // Then: Should be Free tier
        assertThat(freeTier).isEqualTo(FreeSubscriptionTier)
    }
}