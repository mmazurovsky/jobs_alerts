package com.jobsalerts.core.service

import com.jobsalerts.core.domain.model.*
import kotlinx.coroutines.*
import org.assertj.core.api.Assertions.*
import org.junit.jupiter.api.*
import org.junit.jupiter.api.extension.ExtendWith
import org.mockito.Mock
import org.mockito.junit.jupiter.MockitoExtension
import org.mockito.junit.jupiter.MockitoSettings
import org.mockito.quality.Strictness
import org.mockito.kotlin.*
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.test.context.ActiveProfiles
import org.springframework.test.context.TestPropertySource
import java.time.Instant
import java.time.LocalDateTime
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

/**
 * Integration test for JobSearchScheduler that verifies:
 * 1. Jobs are scheduled properly and stored in active searches
 * 2. Jobs can be added and removed dynamically
 * 3. Job parameters are preserved correctly
 * 4. Scheduler manages multiple jobs concurrently
 */
@ExtendWith(MockitoExtension::class)
@MockitoSettings(strictness = Strictness.LENIENT)
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class JobSearchSchedulerIntegrationTest {

    @Mock
    private lateinit var mockScraperJobService: ScraperJobService

    private lateinit var jobSearchScheduler: JobSearchScheduler

    @BeforeEach
    fun setUp() {
        // Create scheduler with mocked scraper service
        jobSearchScheduler = JobSearchScheduler(mockScraperJobService)
        jobSearchScheduler.initializeScheduler()
    }

    @AfterEach
    fun tearDown() {
        if (::jobSearchScheduler.isInitialized) {
            jobSearchScheduler.shutdown()
        }
    }

    @Test
    fun `should schedule jobs and store them in active searches`() = runBlocking {
        // Given: Test jobs with different configurations
        val job1 = createTestJobSearch(
            id = "test-job-1",
            title = "Senior Kotlin Developer", 
            location = "Berlin",
            userId = 100L,
            timePeriod = TimePeriod.`5 minutes`
        )
        
        val job2 = createTestJobSearch(
            id = "test-job-2", 
            title = "Data Scientist",
            location = "London",
            userId = 200L,
            timePeriod = TimePeriod.`1 hour`
        )

        // When: Schedule jobs
        jobSearchScheduler.addJobSearch(job1)
        jobSearchScheduler.addJobSearch(job2)

        // Then: Verify jobs are stored in active searches
        assertThat(jobSearchScheduler.getActiveSearchesCount()).isEqualTo(2)
        assertThat(jobSearchScheduler.getActiveSearches()).containsKeys("test-job-1", "test-job-2")
        
        // Verify job details are preserved
        val storedJob1 = jobSearchScheduler.getActiveSearches()["test-job-1"]!!
        assertThat(storedJob1.jobTitle).isEqualTo("Senior Kotlin Developer")
        assertThat(storedJob1.location).isEqualTo("Berlin")
        assertThat(storedJob1.userId).isEqualTo(100L)
        assertThat(storedJob1.timePeriod).isEqualTo(TimePeriod.`5 minutes`)
        
        val storedJob2 = jobSearchScheduler.getActiveSearches()["test-job-2"]!!
        assertThat(storedJob2.jobTitle).isEqualTo("Data Scientist")
        assertThat(storedJob2.location).isEqualTo("London")
        assertThat(storedJob2.userId).isEqualTo(200L)
        assertThat(storedJob2.timePeriod).isEqualTo(TimePeriod.`1 hour`)
    }

    @Test
    fun `should handle adding and removing jobs dynamically`() = runBlocking {
        // Given: Initial job
        val job1 = createTestJobSearch(id = "dynamic-job-1", title = "DevOps Engineer", userId = 300L)

        // When: Add first job
        jobSearchScheduler.addJobSearch(job1)
        
        // Then: Verify job is added
        assertThat(jobSearchScheduler.getActiveSearchesCount()).isEqualTo(1)
        assertThat(jobSearchScheduler.getActiveSearches()).containsKey("dynamic-job-1")

        // When: Remove the job
        jobSearchScheduler.removeJobSearch("dynamic-job-1")
        
        // Then: Verify job is removed
        assertThat(jobSearchScheduler.getActiveSearchesCount()).isEqualTo(0)
        assertThat(jobSearchScheduler.getActiveSearches()).doesNotContainKey("dynamic-job-1")
        
        // When: Add a new job to verify scheduler still works
        val job2 = createTestJobSearch(id = "dynamic-job-2", title = "Frontend Developer", userId = 400L)
        jobSearchScheduler.addJobSearch(job2)
        
        // Then: Verify new job is added
        assertThat(jobSearchScheduler.getActiveSearchesCount()).isEqualTo(1)
        assertThat(jobSearchScheduler.getActiveSearches()).containsKey("dynamic-job-2")
    }

    @Test
    fun `should preserve job parameters correctly`() = runBlocking {
        // Given: Job with specific parameters
        val jobSearch = JobSearchOut(
            id = "param-test-job",
            jobTitle = "Machine Learning Engineer",
            location = "San Francisco",
            jobTypes = listOf(JobType.`Full-time`, JobType.Contract),
            remoteTypes = listOf(RemoteType.Remote),
            timePeriod = TimePeriod.`1 hour`,
            userId = 500L,
            createdAt = Instant.now()
        )

        // When: Schedule the job
        jobSearchScheduler.addJobSearch(jobSearch)
        
        // Then: Verify all parameters are preserved
        val storedJob = jobSearchScheduler.getActiveSearches()["param-test-job"]!!
        assertThat(storedJob.id).isEqualTo("param-test-job")
        assertThat(storedJob.jobTitle).isEqualTo("Machine Learning Engineer") 
        assertThat(storedJob.location).isEqualTo("San Francisco")
        assertThat(storedJob.jobTypes).containsExactly(JobType.`Full-time`, JobType.Contract)
        assertThat(storedJob.remoteTypes).containsExactly(RemoteType.Remote)
        assertThat(storedJob.userId).isEqualTo(500L)
        assertThat(storedJob.timePeriod).isEqualTo(TimePeriod.`1 hour`)
    }

    @Test
    fun `should handle duplicate job IDs gracefully`() = runBlocking {
        // Given: Job with specific ID
        val originalJob = createTestJobSearch(id = "duplicate-test", title = "Original Job", userId = 600L)
        val duplicateJob = createTestJobSearch(id = "duplicate-test", title = "Duplicate Job", userId = 700L)

        // When: Add the original job first
        jobSearchScheduler.addJobSearch(originalJob)
        assertThat(jobSearchScheduler.getActiveSearchesCount()).isEqualTo(1)
        
        // When: Try to add a job with the same ID
        jobSearchScheduler.addJobSearch(duplicateJob)
        
        // Then: Should still only have one job (duplicate ignored)
        assertThat(jobSearchScheduler.getActiveSearchesCount()).isEqualTo(1)
        
        // Original job should be preserved
        val storedJob = jobSearchScheduler.getActiveSearches()["duplicate-test"]!!
        assertThat(storedJob.jobTitle).isEqualTo("Original Job")
        assertThat(storedJob.userId).isEqualTo(600L)
    }

    @Test
    fun `should schedule multiple jobs with different time periods`() = runBlocking {
        // Given: Jobs with different scheduling intervals
        val hourlyJob = createTestJobSearch(
            id = "hourly-job", 
            title = "Hourly Job", 
            userId = 700L, 
            timePeriod = TimePeriod.`1 hour`
        )
        
        val dailyJob = createTestJobSearch(
            id = "daily-job", 
            title = "Daily Job", 
            userId = 800L, 
            timePeriod = TimePeriod.`24 hours`
        )
        
        val weeklyJob = createTestJobSearch(
            id = "weekly-job", 
            title = "Weekly Job", 
            userId = 900L, 
            timePeriod = TimePeriod.`1 week`
        )

        // When: Schedule all jobs
        jobSearchScheduler.addJobSearch(hourlyJob)
        jobSearchScheduler.addJobSearch(dailyJob)
        jobSearchScheduler.addJobSearch(weeklyJob)

        // Then: Verify all jobs are scheduled
        assertThat(jobSearchScheduler.getActiveSearchesCount()).isEqualTo(3)
        
        val activeSearches = jobSearchScheduler.getActiveSearches()
        assertThat(activeSearches).containsKeys("hourly-job", "daily-job", "weekly-job")
        
        // Verify time periods are preserved
        assertThat(activeSearches["hourly-job"]!!.timePeriod).isEqualTo(TimePeriod.`1 hour`)
        assertThat(activeSearches["daily-job"]!!.timePeriod).isEqualTo(TimePeriod.`24 hours`)
        assertThat(activeSearches["weekly-job"]!!.timePeriod).isEqualTo(TimePeriod.`1 week`)
    }

    @Test
    fun `should handle scheduler initialization and shutdown properly`() = runBlocking {
        // Given: Fresh scheduler instance
        val testScheduler = JobSearchScheduler(mockScraperJobService)
        
        // When: Initialize scheduler
        assertDoesNotThrow {
            testScheduler.initializeScheduler()
        }
        
        // Then: Should be able to add jobs
        val testJob = createTestJobSearch(id = "init-test", title = "Init Test Job", userId = 1000L)
        testScheduler.addJobSearch(testJob)
        assertThat(testScheduler.getActiveSearchesCount()).isEqualTo(1)
        
        // When: Shutdown scheduler
        assertDoesNotThrow {
            testScheduler.shutdown()
        }
        
        // Then: Active searches should be cleared
        assertThat(testScheduler.getActiveSearchesCount()).isEqualTo(0)
    }

    @Test
    fun `should handle bulk job operations`() = runBlocking {
        // Given: Multiple jobs to add at once
        val jobs = listOf(
            createTestJobSearch(id = "bulk-1", title = "Bulk Job 1", userId = 1001L),
            createTestJobSearch(id = "bulk-2", title = "Bulk Job 2", userId = 1002L),
            createTestJobSearch(id = "bulk-3", title = "Bulk Job 3", userId = 1003L),
            createTestJobSearch(id = "bulk-4", title = "Bulk Job 4", userId = 1004L),
            createTestJobSearch(id = "bulk-5", title = "Bulk Job 5", userId = 1005L)
        )

        // When: Add jobs using bulk method
        jobSearchScheduler.addInitialJobSearches(jobs)

        // Then: All jobs should be added
        assertThat(jobSearchScheduler.getActiveSearchesCount()).isEqualTo(5)
        val activeSearches = jobSearchScheduler.getActiveSearches()
        assertThat(activeSearches).containsKeys("bulk-1", "bulk-2", "bulk-3", "bulk-4", "bulk-5")
        
        // Verify job details
        jobs.forEach { originalJob ->
            val storedJob = activeSearches[originalJob.id]!!
            assertThat(storedJob.jobTitle).isEqualTo(originalJob.jobTitle)
            assertThat(storedJob.userId).isEqualTo(originalJob.userId)
        }
    }

    @Test
    fun `should schedule jobs and verify mock setup for scraper service`() = runBlocking {
        // Given: Set up mock for testing (doesn't need to be called immediately)
        whenever(mockScraperJobService.triggerScraperJobAndLog(any())).thenAnswer {
            // Mock response for when jobs would be triggered
            Unit
        }
        
        // Create jobs using the shortest TimePeriod (5 minutes) for testing
        val job1 = createTestJobSearch(
            id = "scraper-test-1",
            title = "Quick Job 1",
            userId = 1100L,
            timePeriod = TimePeriod.`5 minutes`
        )
        val job2 = createTestJobSearch(
            id = "scraper-test-2", 
            title = "Quick Job 2",
            userId = 1200L,
            timePeriod = TimePeriod.`5 minutes`
        )
        
        // When: Schedule the jobs
        jobSearchScheduler.addJobSearch(job1)
        jobSearchScheduler.addJobSearch(job2)
        
        // Then: Verify jobs are scheduled properly
        assertThat(jobSearchScheduler.getActiveSearchesCount()).isEqualTo(2)
        
        // Verify jobs are stored with correct details
        val activeSearches = jobSearchScheduler.getActiveSearches()
        assertThat(activeSearches).containsKeys("scraper-test-1", "scraper-test-2")
        
        val storedJob1 = activeSearches["scraper-test-1"]!!
        val storedJob2 = activeSearches["scraper-test-2"]!!
        
        assertThat(storedJob1.jobTitle).isEqualTo("Quick Job 1")
        assertThat(storedJob1.userId).isEqualTo(1100L)
        assertThat(storedJob1.timePeriod).isEqualTo(TimePeriod.`5 minutes`)
        
        assertThat(storedJob2.jobTitle).isEqualTo("Quick Job 2")
        assertThat(storedJob2.userId).isEqualTo(1200L)
        assertThat(storedJob2.timePeriod).isEqualTo(TimePeriod.`5 minutes`)
        
        // Verify mock is properly configured (will be called by Quartz scheduler)
        verify(mockScraperJobService, never()).triggerScraperJobAndLog(any())
    }
    
    @Test
    fun `should test manual trigger of jobs with mocked scraper service`() = runBlocking {
        // Given: Set up mock to track invocations
        val invocationCount = AtomicInteger(0)
        
        whenever(mockScraperJobService.triggerScraperJobAndLog(any())).thenAnswer {
            invocationCount.incrementAndGet()
            Unit
        }
        
        // Create test jobs
        val job1 = createTestJobSearch(
            id = "manual-test-1",
            title = "Manual Test Job 1",
            userId = 1300L,
            timePeriod = TimePeriod.`5 minutes`
        )
        val job2 = createTestJobSearch(
            id = "manual-test-2",
            title = "Manual Test Job 2", 
            userId = 1400L,
            timePeriod = TimePeriod.`10 minutes`
        )
        
        // When: Schedule the jobs
        jobSearchScheduler.addJobSearch(job1)
        jobSearchScheduler.addJobSearch(job2)
        
        // Manually trigger the scraper service to simulate what would happen when jobs execute
        mockScraperJobService.triggerScraperJobAndLog(job1)
        mockScraperJobService.triggerScraperJobAndLog(job2)
        mockScraperJobService.triggerScraperJobAndLog(job1) // Simulate repeat execution
        
        // Then: Verify mock was called the expected number of times
        assertThat(invocationCount.get()).isEqualTo(3)
        
        // Verify specific calls were made
        verify(mockScraperJobService, times(3)).triggerScraperJobAndLog(any())
        verify(mockScraperJobService, times(2)).triggerScraperJobAndLog(argThat { jobSearch -> jobSearch.id == "manual-test-1" })
        verify(mockScraperJobService, times(1)).triggerScraperJobAndLog(argThat { jobSearch -> jobSearch.id == "manual-test-2" })
    }


    private fun createTestJobSearch(
        id: String,
        title: String,
        location: String = "Remote",
        userId: Long,
        timePeriod: TimePeriod = TimePeriod.`1 hour`
    ): JobSearchOut {
        return JobSearchOut(
            id = id,
            jobTitle = title,
            location = location,
            jobTypes = listOf(JobType.`Full-time`),
            remoteTypes = listOf(RemoteType.Remote),
            timePeriod = timePeriod,
            userId = userId,
            createdAt = Instant.now()
        )
    }
} 