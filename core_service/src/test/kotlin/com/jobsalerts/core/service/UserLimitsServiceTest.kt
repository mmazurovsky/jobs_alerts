package com.jobsalerts.core.service

import com.jobsalerts.core.domain.model.*
import com.jobsalerts.core.repository.JobSearchRepository
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

@ExtendWith(MockitoExtension::class)
class UserLimitsServiceTest {

    @Mock
    private lateinit var userService: UserService

    @Mock
    private lateinit var userSubscriptionService: UserSubscriptionService

    @Mock
    private lateinit var userUsageRepository: UserUsageRepository

    @Mock
    private lateinit var jobSearchRepository: JobSearchRepository

    private lateinit var userLimitsService: UserLimitsService

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
        userLimitsService = UserLimitsService(
            userService = userService,
            userSubscriptionService = userSubscriptionService,
            userUsageRepository = userUsageRepository,
            jobSearchRepository = jobSearchRepository
        )

        // Default mocks - using lenient to avoid UnnecessaryStubbingException
        runBlocking {
            lenient().whenever(userService.getOrCreateUser(testUserId)).thenReturn(testUser)
            lenient().whenever(userSubscriptionService.getCurrentSubscriptionTier(testUserId)).thenReturn(FreeSubscriptionTier)
        }
    }

    @Test
    fun `checkJobAlertLimit should allow creation when user has fewer than 5 alerts on Free tier`() = runBlocking {
        // Given: User has 3 alerts (under the Free tier limit of 5)
        whenever(jobSearchRepository.countByUserId(testUserId)).thenReturn(3L)

        // When: Checking job alert limit
        val result = userLimitsService.checkJobAlertLimit(testUserId)

        // Then: Should allow creation
        assertThat(result.allowed).isTrue()
        assertThat(result.currentUsage).isEqualTo(3)
        assertThat(result.maxAllowed).isEqualTo(5)
        assertThat(result.subscriptionTier).isEqualTo(FreeSubscriptionTier)
        assertThat(result.reason).isNull()
    }

    @Test
    fun `checkJobAlertLimit should allow creation when user has exactly 4 alerts on Free tier`() = runBlocking {
        // Given: User has 4 alerts (one under the Free tier limit of 5)
        whenever(jobSearchRepository.countByUserId(testUserId)).thenReturn(4L)

        // When: Checking job alert limit
        val result = userLimitsService.checkJobAlertLimit(testUserId)

        // Then: Should allow creation
        assertThat(result.allowed).isTrue()
        assertThat(result.currentUsage).isEqualTo(4)
        assertThat(result.maxAllowed).isEqualTo(5)
        assertThat(result.subscriptionTier).isEqualTo(FreeSubscriptionTier)
    }

    @Test
    fun `checkJobAlertLimit should deny creation when user has 5 alerts on Free tier`() = runBlocking {
        // Given: User has 5 alerts (at the Free tier limit)
        whenever(jobSearchRepository.countByUserId(testUserId)).thenReturn(5L)

        // When: Checking job alert limit
        val result = userLimitsService.checkJobAlertLimit(testUserId)

        // Then: Should deny creation
        assertThat(result.allowed).isFalse()
        assertThat(result.currentUsage).isEqualTo(5)
        assertThat(result.maxAllowed).isEqualTo(5)
        assertThat(result.subscriptionTier).isEqualTo(FreeSubscriptionTier)
        assertThat(result.reason).contains("You've reached your limit of 5 job alerts on the Free plan")
    }

    @Test
    fun `checkJobAlertLimit should deny creation when user has more than 5 alerts on Free tier`() = runBlocking {
        // Given: User has 6 alerts (over the Free tier limit - edge case)
        whenever(jobSearchRepository.countByUserId(testUserId)).thenReturn(6L)

        // When: Checking job alert limit
        val result = userLimitsService.checkJobAlertLimit(testUserId)

        // Then: Should deny creation
        assertThat(result.allowed).isFalse()
        assertThat(result.currentUsage).isEqualTo(6)
        assertThat(result.maxAllowed).isEqualTo(5)
        assertThat(result.subscriptionTier).isEqualTo(FreeSubscriptionTier)
        assertThat(result.reason).contains("You've reached your limit of 5 job alerts on the Free plan")
    }

    @Test
    fun `checkDailySearchLimit should allow search when user has fewer than 3 searches today on Free tier`() = runBlocking {
        // Given: User has 1 search today (under the Free tier limit of 3)
        val today = LocalDate.now()
        val todayUsage = UserUsage(
            id = "user-12345-${today}",
            userId = testUser.id,
            date = today.toString(),
            instantSearchesCount = 1,
            createdAt = Instant.now()
        )
        whenever(userUsageRepository.findByUserIdAndDate(testUser.id, today.toString())).thenReturn(todayUsage)

        // When: Checking daily search limit
        val result = userLimitsService.checkDailySearchLimit(testUserId)

        // Then: Should allow search
        assertThat(result.allowed).isTrue()
        assertThat(result.currentUsage).isEqualTo(1)
        assertThat(result.maxAllowed).isEqualTo(3)
        assertThat(result.subscriptionTier).isEqualTo(FreeSubscriptionTier)
        assertThat(result.reason).isNull()
    }

    @Test
    fun `checkDailySearchLimit should allow search when user has exactly 2 searches today on Free tier`() = runBlocking {
        // Given: User has 2 searches today (one under the Free tier limit of 3)
        val today = LocalDate.now()
        val todayUsage = UserUsage(
            id = "user-12345-${today}",
            userId = testUser.id,
            date = today.toString(),
            instantSearchesCount = 2,
            createdAt = Instant.now()
        )
        whenever(userUsageRepository.findByUserIdAndDate(testUser.id, today.toString())).thenReturn(todayUsage)

        // When: Checking daily search limit
        val result = userLimitsService.checkDailySearchLimit(testUserId)

        // Then: Should allow search
        assertThat(result.allowed).isTrue()
        assertThat(result.currentUsage).isEqualTo(2)
        assertThat(result.maxAllowed).isEqualTo(3)
        assertThat(result.subscriptionTier).isEqualTo(FreeSubscriptionTier)
    }

    @Test
    fun `checkDailySearchLimit should deny search when user has 3 searches today on Free tier`() = runBlocking {
        // Given: User has 3 searches today (at the Free tier limit)
        val today = LocalDate.now()
        val todayUsage = UserUsage(
            id = "user-12345-${today}",
            userId = testUser.id,
            date = today.toString(),
            instantSearchesCount = 3,
            createdAt = Instant.now()
        )
        whenever(userUsageRepository.findByUserIdAndDate(testUser.id, today.toString())).thenReturn(todayUsage)

        // When: Checking daily search limit
        val result = userLimitsService.checkDailySearchLimit(testUserId)

        // Then: Should deny search
        assertThat(result.allowed).isFalse()
        assertThat(result.currentUsage).isEqualTo(3)
        assertThat(result.maxAllowed).isEqualTo(3)
        assertThat(result.subscriptionTier).isEqualTo(FreeSubscriptionTier)
        assertThat(result.reason).contains("You've used all 3 daily searches on the Free plan")
    }

    @Test
    fun `checkDailySearchLimit should allow search when user has no usage record for today on Free tier`() = runBlocking {
        // Given: User has no usage record for today (first search of the day)
        val today = LocalDate.now()
        whenever(userUsageRepository.findByUserIdAndDate(testUser.id, today.toString())).thenReturn(null)

        // When: Checking daily search limit
        val result = userLimitsService.checkDailySearchLimit(testUserId)

        // Then: Should allow search
        assertThat(result.allowed).isTrue()
        assertThat(result.currentUsage).isEqualTo(0)
        assertThat(result.maxAllowed).isEqualTo(3)
        assertThat(result.subscriptionTier).isEqualTo(FreeSubscriptionTier)
    }

    @Test
    fun `trackDailySearch should call userUsageRepository incrementDailySearches`() = runBlocking {
        // Given: User service returns test user
        val today = LocalDate.now()

        // When: Tracking daily search
        userLimitsService.trackDailySearch(testUserId)

        // Then: Should call increment method
        verify(userUsageRepository).incrementDailySearches(testUser.id, today)
    }

    @Test
    fun `getCurrentUsage should return correct usage statistics for Free tier user`() = runBlocking {
        // Given: User has some alerts and searches
        val today = LocalDate.now()
        val todayUsage = UserUsage(
            id = "user-12345-${today}",
            userId = testUser.id,
            date = today.toString(),
            instantSearchesCount = 2,
            createdAt = Instant.now()
        )
        whenever(jobSearchRepository.countByUserId(testUserId)).thenReturn(3L)
        whenever(userUsageRepository.findByUserIdAndDate(testUser.id, today.toString())).thenReturn(todayUsage)

        // When: Getting current usage
        val usage = userLimitsService.getCurrentUsage(testUserId)

        // Then: Should return correct statistics
        assertThat(usage.subscriptionTier).isEqualTo(FreeSubscriptionTier)
        assertThat(usage.currentJobAlerts).isEqualTo(3)
        assertThat(usage.maxJobAlerts).isEqualTo(5)
        assertThat(usage.currentDailySearches).isEqualTo(2)
        assertThat(usage.maxDailySearches).isEqualTo(3)
        assertThat(usage.date).isEqualTo(today)
    }

    @Test
    fun `getCurrentUsage should handle user with no usage record for today`() = runBlocking {
        // Given: User has alerts but no searches today
        val today = LocalDate.now()
        whenever(jobSearchRepository.countByUserId(testUserId)).thenReturn(1L)
        whenever(userUsageRepository.findByUserIdAndDate(testUser.id, today.toString())).thenReturn(null)

        // When: Getting current usage
        val usage = userLimitsService.getCurrentUsage(testUserId)

        // Then: Should return zero searches for today
        assertThat(usage.subscriptionTier).isEqualTo(FreeSubscriptionTier)
        assertThat(usage.currentJobAlerts).isEqualTo(1)
        assertThat(usage.currentDailySearches).isEqualTo(0)
        assertThat(usage.maxDailySearches).isEqualTo(3)
    }

    @Test
    fun `Free tier should have correct limits and features`() {
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
    fun `SubscriptionTier fromName should return Free tier for unknown names`() {
        // When: Getting tier by unknown name
        val tier = SubscriptionTier.fromName("UNKNOWN")

        // Then: Should return Free tier as default
        assertThat(tier).isEqualTo(FreeSubscriptionTier)
    }

    @Test
    fun `SubscriptionTier getDefault should return Free tier`() {
        // When: Getting default tier
        val tier = SubscriptionTier.getDefault()

        // Then: Should return Free tier
        assertThat(tier).isEqualTo(FreeSubscriptionTier)
    }
}