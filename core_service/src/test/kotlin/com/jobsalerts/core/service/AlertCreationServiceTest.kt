package com.jobsalerts.core.service

import com.jobsalerts.core.domain.model.*
import com.jobsalerts.core.infrastructure.FromTelegramEventBus
import com.jobsalerts.core.infrastructure.ToTelegramEventBus
import com.jobsalerts.core.repository.JobSearchRepository
import kotlinx.coroutines.*
import org.junit.jupiter.api.*
import org.junit.jupiter.api.extension.ExtendWith
import org.mockito.Mock
import org.mockito.junit.jupiter.MockitoExtension
import org.mockito.junit.jupiter.MockitoSettings
import org.mockito.quality.Strictness
import org.mockito.kotlin.*
import org.assertj.core.api.Assertions.*

@ExtendWith(MockitoExtension::class)
@MockitoSettings(strictness = Strictness.LENIENT)
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class AlertCreationServiceTest {

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

    @Mock
    private lateinit var sessionManager: SessionManager

    private lateinit var alertCreationService: AlertCreationService

    private val testUserId = 42L
    private val testChatId = 123L
    private val testUsername = "testuser"

    @BeforeEach
    fun setUp() {
        alertCreationService = AlertCreationService(
            jobSearchParserService,
            jobSearchRepository,
            jobSearchScheduler,
            fromTelegramEventBus,
            toTelegramEventBus,
            sessionManager
        )
    }

    @Test
    fun `should handle initial create_alert command and send instructions`() {
        runBlocking {
            // Given
            val event = TelegramMessageReceived(
                text = "/create_alert",
                username = testUsername,
                userId = testUserId,
                chatId = testChatId,
                commandName = "/create_alert",
                commandParameters = "",
                message = "test"
            )

            whenever(sessionManager.getCurrentContext(testUserId)).thenReturn(IdleCommandContext)

            // When
            alertCreationService.handleEvent(event)

            // Then
            verify(sessionManager).setContext(testUserId, CreateAlertSubContext.Initial)
            verify(sessionManager).setContext(testUserId, CreateAlertSubContext.CollectingDescription)
            verify(toTelegramEventBus).publish(argThat<ToTelegramSendMessageEvent> { event ->
                event.chatId == testChatId && 
                event.message.contains("Creating a new job alert") &&
                event.message.contains("describe your job search")
            })
        }
    }

    @Test
    fun `should process job description successfully and request confirmation`() {
        runBlocking {
            // Given
            val description = "Senior Kotlin Developer in Berlin, remote, every 1 day"
            val event = TelegramMessageReceived(
                text = description,
                username = testUsername,
                userId = testUserId,
                chatId = testChatId,
                commandName = null,
                commandParameters = "",
                message = "test"
            )

            val expectedJobSearch = JobSearchIn(
                jobTitle = "Senior Kotlin Developer",
                location = "Berlin",
                jobTypes = listOf(JobType.FULL_TIME),
                remoteTypes = listOf(RemoteType.REMOTE),
                timePeriod = TimePeriod.TWENTY_FOUR_HOURS,
                userId = testUserId.toInt(),
                filterText = null
            )

            val parseResult = JobSearchParseResult(
                success = true,
                jobSearchIn = expectedJobSearch
            )

            whenever(sessionManager.getCurrentContext(testUserId)).thenReturn(CreateAlertSubContext.CollectingDescription)
            whenever(jobSearchParserService.parseUserInput(description, testUserId.toInt())).thenReturn(parseResult)

            // When
            alertCreationService.handleEvent(event)

            // Then
            verify(jobSearchParserService).parseUserInput(description, testUserId.toInt())
            verify(sessionManager).updateSession(eq(testUserId), any())
            verify(sessionManager).setContext(testUserId, CreateAlertSubContext.ConfirmingDetails)
            verify(toTelegramEventBus, times(2)).publish(any<ToTelegramSendMessageEvent>())
            
            // Verify the analyzing message
            verify(toTelegramEventBus).publish(argThat<ToTelegramSendMessageEvent> { event ->
                event.chatId == testChatId && event.message.contains("Analyzing your job alert description")
            })
            
            // Verify the confirmation message
            verify(toTelegramEventBus).publish(argThat<ToTelegramSendMessageEvent> { event ->
                event.chatId == testChatId && 
                event.message.contains("Job alert parsed successfully") &&
                event.message.contains("Is this correct?")
            })
        }
    }

    @Test
    fun `should handle parse failure and request retry`() {
        runBlocking {
            // Given
            val description = "invalid description"
            val event = TelegramMessageReceived(
                text = description,
                username = testUsername,
                userId = testUserId,
                chatId = testChatId,
                commandName = null,
                commandParameters = "",
                message = "test"
            )

            val parseResult = JobSearchParseResult(
                success = false,
                errorMessage = "Missing required information",
                missingFields = listOf("Job Title", "Location")
            )

            whenever(sessionManager.getCurrentContext(testUserId)).thenReturn(CreateAlertSubContext.CollectingDescription)
            whenever(jobSearchParserService.parseUserInput(description, testUserId.toInt())).thenReturn(parseResult)
            whenever(sessionManager.getSession(testUserId, testChatId, "")).thenReturn(
                UserSession(
                    userId = testUserId,
                    chatId = testChatId,
                    username = testUsername,
                    context = CreateAlertSubContext.CollectingDescription,
                    retryCount = 0
                )
            )

            // When
            alertCreationService.handleEvent(event)

            // Then
            verify(jobSearchParserService).parseUserInput(description, testUserId.toInt())
            verify(sessionManager).updateSession(eq(testUserId), any())
            verify(toTelegramEventBus, times(2)).publish(any<ToTelegramSendMessageEvent>())
            
            // Verify error message
            verify(toTelegramEventBus).publish(argThat<ToTelegramSendMessageEvent> { event ->
                event.chatId == testChatId && 
                event.message.contains("Missing required information") &&
                event.message.contains("Job Title, Location")
            })
        }
    }

    @Test
    fun `should create alert when user confirms with yes`() {
        runBlocking {
            // Given
            val confirmationEvent = TelegramMessageReceived(
                text = "yes",
                username = testUsername,
                userId = testUserId,
                chatId = testChatId,
                commandName = null,
                commandParameters = "",
                message = "test"
            )

            val pendingJobSearch = JobSearchIn(
                jobTitle = "Senior Kotlin Developer",
                location = "Berlin",
                jobTypes = listOf(JobType.FULL_TIME),
                remoteTypes = listOf(RemoteType.REMOTE),
                timePeriod = TimePeriod.TWENTY_FOUR_HOURS,
                userId = testUserId.toInt(),
                filterText = null
            )

            val sessionWithPending = UserSession(
                userId = testUserId,
                chatId = testChatId,
                username = testUsername,
                context = CreateAlertSubContext.ConfirmingDetails,
                pendingJobSearch = pendingJobSearch,
                retryCount = 0,
                createdAt = System.currentTimeMillis(),
                updatedAt = System.currentTimeMillis()
            )

            val savedJobSearch = JobSearchOut.fromJobSearchIn(pendingJobSearch).copy(id = "test-id-123")

            whenever(sessionManager.getCurrentContext(testUserId)).thenReturn(CreateAlertSubContext.ConfirmingDetails)
            whenever(sessionManager.getSession(testUserId, testChatId, testUsername)).thenReturn(sessionWithPending)
            whenever(jobSearchRepository.save(any<JobSearchOut>())).thenReturn(savedJobSearch)

            // When
            alertCreationService.handleEvent(confirmationEvent)

            // Then
            verify(jobSearchRepository).save(any<JobSearchOut>())
            verify(jobSearchScheduler).addJobSearch(savedJobSearch)
            verify(sessionManager).resetToIdle(testUserId)
            verify(toTelegramEventBus, times(2)).publish(any<ToTelegramSendMessageEvent>())
            
            // Verify success message
            verify(toTelegramEventBus).publish(argThat<ToTelegramSendMessageEvent> { event ->
                event.chatId == testChatId && 
                event.message.contains("Job alert created successfully") &&
                event.message.contains("test-id-123")
            })
        }
    }

    @Test
    fun `should retry when user responds with no`() {
        runBlocking {
            // Given
            val confirmationEvent = TelegramMessageReceived(
                text = "no",
                username = testUsername,
                userId = testUserId,
                chatId = testChatId,
                commandName = null,
                commandParameters = "",
                message = "test"
            )

            val pendingJobSearch = JobSearchIn(
                jobTitle = "Senior Kotlin Developer",
                location = "Berlin",
                jobTypes = listOf(JobType.FULL_TIME),
                remoteTypes = listOf(RemoteType.REMOTE),
                timePeriod = TimePeriod.TWENTY_FOUR_HOURS,
                userId = testUserId.toInt(),
                filterText = null
            )

            val sessionWithPending = UserSession(
                userId = testUserId,
                chatId = testChatId,
                username = testUsername,
                context = CreateAlertSubContext.ConfirmingDetails,
                pendingJobSearch = pendingJobSearch,
                retryCount = 0,
                createdAt = System.currentTimeMillis(),
                updatedAt = System.currentTimeMillis()
            )

            whenever(sessionManager.getCurrentContext(testUserId)).thenReturn(CreateAlertSubContext.ConfirmingDetails)
            whenever(sessionManager.getSession(testUserId, testChatId, testUsername)).thenReturn(sessionWithPending)

            // When
            alertCreationService.handleEvent(confirmationEvent)

            // Then
            verify(sessionManager).updateSession(eq(testUserId), any())
            verify(toTelegramEventBus).publish(argThat<ToTelegramSendMessageEvent> { event ->
                event.chatId == testChatId && 
                event.message.contains("Let's modify your job alert")
            })
            verifyNoInteractions(jobSearchRepository)
            verifyNoInteractions(jobSearchScheduler)
        }
    }

    @Test
    fun `should handle cancel command and reset session`() {
        runBlocking {
            // Given
            val cancelEvent = TelegramMessageReceived(
                text = "/cancel",
                username = testUsername,
                userId = testUserId,
                chatId = testChatId,
                commandName = "/cancel",
                commandParameters = "",
                message = "test"
            )

            // Set context to CollectingDescription so the cancel condition matches
            whenever(sessionManager.getCurrentContext(testUserId)).thenReturn(CreateAlertSubContext.CollectingDescription)

            // When
            alertCreationService.handleEvent(cancelEvent)

            // Then
            verify(sessionManager).resetToIdle(testUserId)
            verify(toTelegramEventBus).publish(argThat<ToTelegramSendMessageEvent> { event ->
                event.chatId == testChatId && 
                event.message.contains("Alert creation cancelled")
            })
            // Verify that JobSearchParserService was NOT called since we're cancelling
            verifyNoInteractions(jobSearchParserService)
        }
    }

    @Test
    fun `should handle multiple parse failures and show structured fallback`() {
        runBlocking {
            // Given
            val description = "invalid description"
            val event = TelegramMessageReceived(
                text = description,
                username = testUsername,
                userId = testUserId,
                chatId = testChatId,
                commandName = null,
                commandParameters = "",
                message = "test"
            )

            val sessionWithRetries = UserSession(
                userId = testUserId,
                chatId = testChatId,
                username = testUsername,
                context = CreateAlertSubContext.CollectingDescription,
                pendingJobSearch = null,
                retryCount = 2, // Already 2 retries, next will be 3rd
                createdAt = System.currentTimeMillis(),
                updatedAt = System.currentTimeMillis()
            )

            val parseResult = JobSearchParseResult(
                success = false,
                errorMessage = "Cannot parse description"
            )

            whenever(sessionManager.getCurrentContext(testUserId)).thenReturn(CreateAlertSubContext.CollectingDescription)
            whenever(sessionManager.getSession(testUserId, testChatId, "")).thenReturn(sessionWithRetries)
            whenever(jobSearchParserService.parseUserInput(description, testUserId.toInt())).thenReturn(parseResult)

            // When
            alertCreationService.handleEvent(event)

            // Then
            verify(sessionManager).updateSession(eq(testUserId), any())
            verify(toTelegramEventBus, times(2)).publish(any<ToTelegramSendMessageEvent>())
            
            // Verify fallback structured approach message
            verify(toTelegramEventBus).publish(argThat<ToTelegramSendMessageEvent> { event ->
                event.chatId == testChatId && 
                event.message.contains("structured approach") &&
                event.message.contains("Job Title:") &&
                event.message.contains("Location:")
            })
        }
    }

    @Test
    fun `should handle confirmation with missing pending job search`() {
        runBlocking {
            // Given
            val confirmationEvent = TelegramMessageReceived(
                text = "yes",
                username = testUsername,
                userId = testUserId,
                chatId = testChatId,
                commandName = null,
                commandParameters = "",
                message = "test"
            )

            val sessionWithoutPending = UserSession(
                userId = testUserId,
                chatId = testChatId,
                username = testUsername,
                context = CreateAlertSubContext.ConfirmingDetails,
                pendingJobSearch = null, // No pending job search
                retryCount = 0,
                createdAt = System.currentTimeMillis(),
                updatedAt = System.currentTimeMillis()
            )

            whenever(sessionManager.getCurrentContext(testUserId)).thenReturn(CreateAlertSubContext.ConfirmingDetails)
            whenever(sessionManager.getSession(testUserId, testChatId, testUsername)).thenReturn(sessionWithoutPending)

            // When
            alertCreationService.handleEvent(confirmationEvent)

            // Then
            verify(sessionManager).resetToIdle(testUserId)
            verify(toTelegramEventBus).publish(argThat<ToTelegramSendMessageEvent> { event ->
                event.chatId == testChatId && 
                event.message.contains("No pending job alert found")
            })
            verifyNoInteractions(jobSearchRepository)
            verifyNoInteractions(jobSearchScheduler)
        }
    }
} 