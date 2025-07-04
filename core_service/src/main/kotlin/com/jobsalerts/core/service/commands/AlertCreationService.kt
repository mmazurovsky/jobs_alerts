package com.jobsalerts.core.service

import com.jobsalerts.core.Messages
import com.jobsalerts.core.domain.model.*
import com.jobsalerts.core.infrastructure.FromTelegramEventBus
import com.jobsalerts.core.infrastructure.ToTelegramEventBus
import com.jobsalerts.core.repository.JobSearchRepository
import jakarta.annotation.PostConstruct
import jakarta.annotation.PreDestroy
import kotlinx.coroutines.*
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.stereotype.Service

@Service
class AlertCreationService(
    private val jobSearchParserService: JobSearchParserService,
    private val jobSearchRepository: JobSearchRepository,
    private val jobSearchScheduler: JobSearchScheduler,
    private val fromTelegramEventBus: FromTelegramEventBus,
    private val toTelegramEventBus: ToTelegramEventBus,
    private val sessionManager: SessionManager
) : Logging {

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var eventSubscription: Job? = null

    @PostConstruct
    fun initialize() {
        eventSubscription =
            fromTelegramEventBus.subscribe(serviceScope) { event -> handleEvent(event) }
        logger.info { "AlertCreationService initialized and subscribed to events" }
    }

    @PreDestroy
    fun cleanup() {
        eventSubscription?.cancel()
        serviceScope.cancel()
        logger.info { "AlertCreationService cleanup completed" }
    }

    internal suspend fun handleEvent(event: FromTelegramEvent) {
        if (event is TelegramMessageReceived) {
            val initialDescription = event.commandParameters?.trim()
            val currentContext = sessionManager.getCurrentContext(event.userId)

            when {
                // Handle /create_alert commands
                event.commandName == "/cancel" && currentContext is CreateAlertSubContext -> {
                    logger.info { "🔔 AlertCreationService: Processing /cancel command" }
                    sendMessage(event.chatId, Messages.CANCEL_MESSAGE)
                    sessionManager.resetToIdle(event.userId)
                }

                event.commandName == "/create_alert" && initialDescription.isNullOrEmpty() -> {
                    logger.info { "🔔 AlertCreationService: Processing /create_alert command (no parameters)" }
                    sessionManager.setContext(
                        event.chatId,
                        event.userId,
                        CreateAlertSubContext.Initial
                    )
                    processInitial(event)
                }

                event.commandName == "/create_alert" && !initialDescription.isNullOrEmpty() -> {
                    logger.info { "🔔 AlertCreationService: Processing /create_alert command with parameters: $initialDescription" }
                    sessionManager.setContext(
                        event.chatId,
                        event.userId,
                        CreateAlertSubContext.CollectingDescription
                    )
                    processAlertDescription(event.chatId, event.userId, event.text)
                }

                // Handle context-based plain text messages
                event.commandName == null && currentContext is CreateAlertSubContext.CollectingDescription -> {
                    logger.info { "🔔 AlertCreationService: Handling description collection in context: '${event.text}'" }
                    processAlertDescription(event.chatId, event.userId, event.text)
                }

                event.commandName == null && currentContext is CreateAlertSubContext.ConfirmingDetails -> {
                    logger.info { "🔔 AlertCreationService: Handling confirmation in context: '${event.text}'" }
                    processConfirmation(event.chatId, event.userId, event.username, event.text)
                }
            }
        }
    }

    private suspend fun processInitial(event: TelegramMessageReceived) {
        try {
            sendMessage(event.chatId, Messages.getCreateAlertInstructions())
            sessionManager.setContext(
                chatId = event.chatId,
                userId = event.userId,
                context = CreateAlertSubContext.CollectingDescription
            )
        } catch (e: Exception) {
            logger.error(e) { "Error sending initial instructions to user $event.userId" }
        }
    }

    private suspend fun sendMessage(chatId: Long, message: String) {
        toTelegramEventBus.publish(
            ToTelegramSendMessageEvent(
                message = message,
                chatId = chatId,
                eventSource = "AlertCreationService"
            )
        )
    }

    private suspend fun processAlertDescription(chatId: Long, userId: Long, description: String) {
        try {
            sendMessage(chatId, Messages.ANALYZING_DESCRIPTION)

            val parseResult = jobSearchParserService.parseUserInput(description, userId)

            if (parseResult.success && parseResult.jobSearchIn != null) {
                logger.info { "🔔 AlertCreationService: No frequency specified, asking user to select" }
                sessionManager.updateSession(userId) { session ->
                    session.copy(pendingJobSearch = parseResult.jobSearchIn, retryCount = 0)
                }
                sessionManager.setContext(
                    chatId = chatId,
                    userId = userId,
                    context = CreateAlertSubContext.ConfirmingDetails
                )

                // Show confirmation with parsed data
                sendMessage(chatId, Messages.getAlertCreationConfirmation(parseResult.jobSearchIn))
            } else {
                // Parsing failed, ask for retry
                handleParseFailure(chatId, userId, parseResult)
            }
        } catch (e: Exception) {
            logger.error(e) { "Error processing alert description for user $userId" }
            sendMessage(chatId, Messages.ERROR_GENERAL)
        }
    }

    private suspend fun processConfirmation(
        chatId: Long,
        userId: Long,
        username: String?,
        confirmation: String
    ) {
        val session = sessionManager.getSession(userId, chatId, username)
        val jobSearch = session.pendingJobSearch

        if (jobSearch == null) {
            sendMessage(chatId, Messages.ERROR_NO_PENDING_ALERT)
            sessionManager.resetToIdle(userId)
            return
        }

        val lowerConfirmation = confirmation.lowercase().trim()

        when {
            lowerConfirmation in listOf("yes", "y", "confirm", "ok", "proceed") -> {
                try {
                    sendMessage(chatId, Messages.CREATING_ALERT)

                    val alertId = createJobAlert(jobSearch)
                    sendMessage(chatId, Messages.getAlertCreatedSuccess(alertId, jobSearch))
                    sessionManager.resetToIdle(userId)
                } catch (e: Exception) {
                    logger.error(e) { "Error creating job alert for user $userId" }
                    sendMessage(chatId, Messages.ERROR_CREATION_FAILED)
                    sessionManager.resetToIdle(userId)
                }
            }

            lowerConfirmation in listOf("no", "n", "cancel", "modify", "change") -> {
                sendMessage(chatId, Messages.getRetryJobAlertMessage())
                sessionManager.updateSession(userId) { session ->
                    session.copy(pendingJobSearch = null, retryCount = session.retryCount + 1)
                }
                sessionManager.setContext(
                    chatId = userId,
                    userId = userId,
                    context = CreateAlertSubContext.CollectingDescription
                )
            }

            else -> {
                sendMessage(chatId, Messages.getConfirmationInstruction("create"))
            }
        }
    }

    private suspend fun createJobAlert(input: JobSearchIn): String {
        val jobSearch = JobSearchOut.fromJobSearchIn(input)

        val saved = jobSearchRepository.save(jobSearch)
        logger.info { "Created job search: ${saved.toLogString()}" }

        // Add to scheduler using new method
        jobSearchScheduler.addJobSearch(saved)

        return saved.id
    }

    private suspend fun handleParseFailure(
        chatId: Long,
        userId: Long,
        parseResult: JobSearchParseResult
    ) {
        val session = sessionManager.getSession(userId, chatId, "")
        val newRetryCount = session.retryCount + 1

        if (newRetryCount >= 3) {
            sendMessage(chatId, Messages.getStructuredApproachMessage())
            sessionManager.updateSession(userId) { session ->
                session.copy(retryCount = newRetryCount)
            }
        } else {
            sendMessage(chatId, Messages.getParseErrorMessageForAlert(parseResult))
            sessionManager.updateSession(userId) { session ->
                session.copy(retryCount = newRetryCount)
            }
        }
    }
}
