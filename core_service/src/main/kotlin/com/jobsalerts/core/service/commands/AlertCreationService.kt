package com.jobsalerts.core.service

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
                    sendMessage(event.chatId, "❌ Alert creation cancelled.")
                    sessionManager.resetToIdle(event.userId)
                }
                event.commandName == "/create_alert" && initialDescription.isNullOrEmpty() -> {
                    logger.info { "🔔 AlertCreationService: Processing /create_alert command (no parameters)" }
                    sessionManager.setContext(event.chatId, event.userId, CreateAlertSubContext.Initial)
                    processInitial(event)
                }
                event.commandName == "/create_alert" && !initialDescription.isNullOrEmpty() -> {
                    logger.info { "🔔 AlertCreationService: Processing /create_alert command with parameters: $initialDescription" }
                    sessionManager.setContext(event.chatId, event.userId, CreateAlertSubContext.CollectingDescription)
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
        val instructionsMessage = buildString {
            appendLine("🔔 **Creating a new job alert**")
            appendLine()
            append(JobSearchIn.getFormattingInstructions())
            appendLine()
            appendLine(
                    "💡 **Note:** This will create a recurring alert that searches for jobs automatically!"
            )
        }
        try {
            sendMessage(event.chatId, instructionsMessage)
            sessionManager.setContext(chatId = event.chatId, userId = event.userId, context = CreateAlertSubContext.CollectingDescription)
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
            sendMessage(chatId, "🔍 Analyzing your job alert description...")

            val parseResult = jobSearchParserService.parseUserInput(description, userId)

            if (parseResult.success && parseResult.jobSearchIn != null) {                
                    sessionManager.updateSession(userId) { session ->
                        session.copy(pendingJobSearch = parseResult.jobSearchIn, retryCount = 0)
                    }
                    sessionManager.setContext(chatId = chatId, userId = userId, context = CreateAlertSubContext.ConfirmingDetails)
                    showConfirmationMessage(chatId, userId, parseResult.jobSearchIn)
                }
             else {
                handleParseFailure(chatId, userId, parseResult)
            }
        } catch (e: Exception) {
            logger.error(e) { "Error processing alert description for user $userId" }
            sendMessage(
                    chatId,
                    "❌ An error occurred while processing your request. Please try again or use /cancel to abort."
            )
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
            sendMessage(
                    chatId,
                    "❌ No pending job alert found. Please start over with /create_alert"
            )
            sessionManager.resetToIdle(userId)
            return
        }

        val lowerConfirmation = confirmation.lowercase().trim()

        when {
            lowerConfirmation in listOf("yes", "y", "confirm", "ok", "proceed") -> {
                try {
                    sendMessage(chatId, "🔔 **Creating your job alert...**")

                    val alertId = createJobAlert(jobSearch)

                    val successMessage = buildString {
                        appendLine("✅ **Job alert created successfully!**")
                        appendLine()
                        appendLine("📋 **Alert ID:** $alertId")
                        appendLine("🔍 **Searching for:** ${jobSearch.jobTitle}")
                        appendLine("📍 **Location:** ${jobSearch.location}")
                        appendLine("⏰ **Frequency:** ${jobSearch.timePeriod.displayName}")
                        appendLine()
                        appendLine(
                                "🔔 You'll receive notifications when new jobs matching your criteria are found."
                        )
                        appendLine()
                        appendLine(
                                "Use /list_alerts to see all your alerts or /menu for other options."
                        )
                    }

                    sendMessage(chatId, successMessage)
                    sessionManager.resetToIdle(userId)
                } catch (e: Exception) {
                    logger.error(e) { "Error creating job alert for user $userId" }
                    sendMessage(
                            chatId,
                            "❌ Failed to create job alert. Please try again later or contact support."
                    )
                    sessionManager.resetToIdle(userId)
                }
            }
            lowerConfirmation in listOf("no", "n", "cancel", "modify", "change") -> {
                val retryMessage = buildString {
                    appendLine("📝 **Let's modify your job alert.**")
                    appendLine()
                    append(JobSearchIn.getFormattingInstructions())
                }

                sessionManager.updateSession(userId) { session ->
                    session.copy(pendingJobSearch = null, retryCount = session.retryCount + 1, context = CreateAlertSubContext.CollectingDescription)
                }

                sendMessage(chatId, retryMessage)
            }
            else -> {
                sendMessage(
                        chatId,
                        "Please respond with '**yes**' to create the alert, '**no**' to modify, or /cancel to abort."
                )
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
    
    private suspend fun showConfirmationMessage(chatId: Long, userId: Long, jobSearchIn: JobSearchIn) {
        val confirmationMessage = buildString {
            appendLine("✅ **Job alert parsed successfully!**")
            appendLine()
            append(jobSearchIn.toHumanReadableString())
            appendLine()
            appendLine("**Is this correct?**")
            appendLine("• Reply '**yes**' to create the alert")
            appendLine("• Reply '**no**' to modify your alert")
            appendLine("• Use /cancel to abort")
        }

        sessionManager.updateSession(userId) { session ->
            session.copy(pendingJobSearch = jobSearchIn, retryCount = 0)
        }
        sessionManager.setContext(chatId = chatId, userId = userId, context = CreateAlertSubContext.ConfirmingDetails)

        sendMessage(chatId, confirmationMessage)
    }

    private suspend fun handleParseFailure(
            chatId: Long,
            userId: Long,
            parseResult: JobSearchParseResult
    ) {
        val session = sessionManager.getSession(userId, chatId, "")
        val newRetryCount = session.retryCount + 1

        if (newRetryCount >= 3) {
            val fallbackMessage = buildString {
                appendLine("❌ **I'm having trouble understanding your job alert description.**")
                appendLine()
                appendLine("Let's try a structured approach. Please provide:")
                appendLine()
                appendLine("**Job Title:** [What position are you looking for?]")
                appendLine("**Location:** [Where do you want to work?]")
                appendLine("**Job Type:** [Full-time, Part-time, Contract, etc.]")
                appendLine("**Remote Type:** [Remote, On-site, Hybrid]")
                appendLine("**Additional Requirements:** [Any other requirements or keywords]")
                appendLine()
                appendLine("Use /cancel if you want to stop.")
            }

            sessionManager.updateSession(userId) { session ->
                session.copy(retryCount = newRetryCount)
            }

            sendMessage(chatId, fallbackMessage)
        } else {
            val errorMessage = buildString {
                appendLine("❌ **${parseResult.errorMessage}**")
                appendLine()
                if (parseResult.missingFields.isNotEmpty()) {
                    appendLine(
                            "**Missing information:** ${parseResult.missingFields.joinToString(", ")}"
                    )
                    appendLine()
                }
                appendLine("Please try again with a clearer description:")
                appendLine()
                appendLine("**Examples:**")
                appendLine(
                        "• \"Senior Software Engineer in San Francisco, full-time, remote, \$150k+, no on-call\""
                )
                appendLine(
                        "• \"Data Scientist role in Berlin, contract work, English speaking, avoid startups\""
                )
                appendLine(
                        "• \"Product Manager in New York, full-time, on-site, health insurance required\""
                )
                appendLine()
                appendLine("Or use /cancel to stop.")
            }

            sessionManager.updateSession(userId) { session ->
                session.copy(retryCount = newRetryCount)
            }

            sendMessage(chatId, errorMessage)
        }
    }
}
