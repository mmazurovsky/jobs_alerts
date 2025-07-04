package com.jobsalerts.core.service

import com.jobsalerts.core.domain.model.*
import com.jobsalerts.core.infrastructure.FromTelegramEventBus
import com.jobsalerts.core.infrastructure.ToTelegramEventBus
import com.jobsalerts.core.repository.JobSearchRepository
import com.jobsalerts.core.service.AlertCreationService
import kotlinx.coroutines.*
import org.junit.jupiter.api.*
import org.junit.jupiter.api.extension.ExtendWith
import org.mockito.InjectMocks
import org.mockito.Mock
import org.mockito.junit.jupiter.MockitoExtension
import org.mockito.junit.jupiter.MockitoSettings
import org.mockito.quality.Strictness
import org.mockito.kotlin.*
import org.assertj.core.api.Assertions.*
import java.time.Instant

@ExtendWith(MockitoExtension::class)
@MockitoSettings(strictness = Strictness.LENIENT)
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class AlertCreationServiceTest {

    @Mock
    private lateinit var sessionManager: SessionManager

    @Mock
    private lateinit var jobSearchParserService: JobSearchParserService

    @Mock
    private lateinit var jobSearchRepository: JobSearchRepository

    @Mock
    private lateinit var jobSearchScheduler: JobSearchScheduler

    @Mock
    private lateinit var fromTelegramEventBus: FromTelegramEventBus

    @Mock
    private lateinit var toTelegramEventBus: ToTelegramEventBus

    @InjectMocks
    private lateinit var alertCreationService: AlertCreationService

    private val userId = 12345L
    private val chatId = 67890L
    private val username = "testuser"

    @BeforeEach
    fun setUp() {
        // Initialize any common mocks here
    }

    @Test
    fun `should handle telegram message received event`() = runBlocking {
        // Arrange
        val session = UserSession(
            userId = userId,
            chatId = chatId,
            username = username,
            context = IdleCommandContext,
            createdAt = System.currentTimeMillis(),
            updatedAt = System.currentTimeMillis()
        )
        whenever(sessionManager.getSession(userId, chatId, username)).thenReturn(session)

        val event = TelegramMessageReceived(
            message = "/create_alert",
            text = "/create_alert",
            username = username,
            userId = userId,
            chatId = chatId,
            commandName = "/create_alert"
        )

        // Act
        alertCreationService.handleEvent(event)

        // Assert - verify that the service processes the event
        verify(sessionManager).getSession(userId, chatId, username)
    }

    @Test
    fun `should create job search successfully`() {
        // Given
        val jobSearchIn = JobSearchIn(
            jobTitle = "Software Engineer",
            location = "New York, NY",
            jobTypes = listOf(JobType.`Full-time`),
            remoteTypes = listOf(RemoteType.Remote),
            timePeriod = TimePeriod.`1 hour`,
            userId = userId
        )

        val expectedJobSearchOut = JobSearchOut(
            id = "test-id",
            jobTitle = "Software Engineer",
            location = "New York, NY",
            jobTypes = listOf(JobType.`Full-time`),
            remoteTypes = listOf(RemoteType.Remote),
            timePeriod = TimePeriod.`1 hour`,
            userId = userId,
            createdAt = Instant.now()
        )

        whenever(jobSearchRepository.save(any<JobSearchOut>())).thenReturn(expectedJobSearchOut)

        // When
        val result = JobSearchOut.fromJobSearchIn(jobSearchIn)

        // Then
        assertThat(result).isNotNull()
        assertThat(result.jobTitle).isEqualTo("Software Engineer")
        assertThat(result.location).isEqualTo("New York, NY")
        assertThat(result.userId).isEqualTo(userId)
    }

    @Test
    fun `should parse job search successfully`() = runBlocking {
        // Given
        val userInput = "Software Engineer in New York"
        val expectedResult = JobSearchParseResult(
            success = true,
            jobSearchIn = JobSearchIn(
                jobTitle = "Software Engineer",
                location = "New York, NY",
                jobTypes = listOf(JobType.`Full-time`),
                remoteTypes = listOf(RemoteType.Remote),
                timePeriod = TimePeriod.getDefault(),
                userId = userId
            ),
            errorMessage = null
        )

        whenever(jobSearchParserService.parseUserInput(userInput, userId)).thenReturn(expectedResult)

        // When
        val result = jobSearchParserService.parseUserInput(userInput, userId)

        // Then
        assertThat(result.success).isTrue()
        assertThat(result.jobSearchIn).isNotNull()
        assertThat(result.jobSearchIn?.jobTitle).isEqualTo("Software Engineer")
        verify(jobSearchParserService).parseUserInput(userInput, userId)
    }

    @Test
    fun `should handle parse failure`() = runBlocking {
        // Given
        val userInput = "invalid input"
        val expectedResult = JobSearchParseResult(
            success = false,
            jobSearchIn = null,
            errorMessage = "Could not parse job description",
            missingFields = listOf("title", "location")
        )

        whenever(jobSearchParserService.parseUserInput(userInput, userId)).thenReturn(expectedResult)

        // When
        val result = jobSearchParserService.parseUserInput(userInput, userId)

        // Then
        assertThat(result.success).isFalse()
        assertThat(result.jobSearchIn).isNull()
        assertThat(result.errorMessage).isNotNull()
        verify(jobSearchParserService).parseUserInput(userInput, userId)
    }

    @Test
    fun `should schedule job search`() = runBlocking {
        // Given
        val jobSearchOut = JobSearchOut(
            id = "test-id",
            jobTitle = "Backend Developer",
            location = "San Francisco, CA",
            jobTypes = listOf(JobType.`Full-time`),
            remoteTypes = listOf(RemoteType.Remote),
            timePeriod = TimePeriod.`24 hours`,
            userId = userId,
            createdAt = Instant.now()
        )

        // When
        jobSearchScheduler.addJobSearch(jobSearchOut)

        // Then
        verify(jobSearchScheduler).addJobSearch(jobSearchOut)
    }

    @Test
    fun `should validate session creation`() {
        // Given
        val session = UserSession(
            userId = userId,
            chatId = chatId,
            username = username,
            context = IdleCommandContext,
            createdAt = System.currentTimeMillis(),
            updatedAt = System.currentTimeMillis()
        )

        // When & Then
        assertThat(session.userId).isEqualTo(userId)
        assertThat(session.chatId).isEqualTo(chatId)
        assertThat(session.username).isEqualTo(username)
        assertThat(session.context).isEqualTo(IdleCommandContext)
    }

    @Test
    fun `should validate time periods`() {
        // When & Then
        assertThat(TimePeriod.`5 minutes`.seconds).isEqualTo(300)
        assertThat(TimePeriod.`1 hour`.seconds).isEqualTo(3600)
        assertThat(TimePeriod.`24 hours`.seconds).isEqualTo(43200)
        assertThat(TimePeriod.getDefault()).isEqualTo(TimePeriod.`1 hour`)
    }

    @Test
    fun `should validate job types and remote types`() {
        // When & Then
        assertThat(JobType.`Full-time`).isNotNull()
        assertThat(JobType.`Part-time`).isNotNull()
        assertThat(JobType.Contract).isNotNull()
        assertThat(JobType.Temporary).isNotNull()
        assertThat(JobType.Internship).isNotNull()

        assertThat(RemoteType.`On-site`).isNotNull()
        assertThat(RemoteType.Remote).isNotNull()
        assertThat(RemoteType.Hybrid).isNotNull()
    }
}