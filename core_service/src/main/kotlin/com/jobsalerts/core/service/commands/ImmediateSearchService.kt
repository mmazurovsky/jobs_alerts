package com.jobsalerts.core.service

import com.jobsalerts.core.Messages
import com.jobsalerts.core.domain.model.*
import com.jobsalerts.core.infrastructure.FromTelegramEventBus
import com.jobsalerts.core.infrastructure.ToTelegramEventBus
import jakarta.annotation.PostConstruct
import jakarta.annotation.PreDestroy
import kotlinx.coroutines.*
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.stereotype.Service

@Service
class ImmediateSearchService(
    private val jobSearchParserService: JobSearchParserService,
    private val scraperJobService: ScraperJobService,
    private val fromTelegramEventBus: FromTelegramEventBus,
    private val toTelegramEventBus: ToTelegramEventBus,
    private val sessionManager: SessionManager,
    private val userLimitsService: UserLimitsService
) : Logging {

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var eventSubscription: Job? = null

    @PostConstruct
    fun initialize() {
        eventSubscription = fromTelegramEventBus.subscribe(serviceScope) { event ->
            handleEvent(event)
        }
        logger.info { "ImmediateSearchService initialized and subscribed to events" }
    }

    @PreDestroy
    fun cleanup() {
        eventSubscription?.cancel()
        serviceScope.cancel()
        logger.info { "ImmediateSearchService cleanup completed" }
    }

    private suspend fun handleEvent(event: FromTelegramEvent) {
        if (event is TelegramMessageReceived) {
            val initialDescription = event.commandParameters?.trim()
            val currentContext = sessionManager.getCurrentContext(event.userId)
            
            logger.info { "🔍 ImmediateSearchService: Processing event - commandName='${event.commandName}', context=$currentContext, userId=${event.userId}" }
            
            when {
                // Handle /search_now commands
                event.commandName == "/search_now" && initialDescription.isNullOrEmpty() -> {
                    logger.info { "🔍 ImmediateSearchService: Processing /search_now command (no parameters)" }
                    sessionManager.setContext(chatId = event.chatId, userId = event.userId, context = SearchNowSubContext.Initial)
                    try {
                        processInitial(event)
                    } catch (e: Exception) {
                        logger.error(e) { "Error processing initial search for user ${event.userId}" }
                    }
                }

                event.commandName == "/search_now" && !initialDescription.isNullOrEmpty() -> {
                    logger.info { "🔍 ImmediateSearchService: Processing /search_now command with parameters: $initialDescription" }
                    sessionManager.setContext(chatId = event.chatId, userId = event.userId, context = SearchNowSubContext.CollectingDescription)
                    processJobSearchDescription(event.chatId, event.userId, event.text)
                }
                
                // Handle context-based plain text messages
                event.commandName == null && currentContext is SearchNowSubContext.CollectingDescription -> {
                    logger.info { "🔍 ImmediateSearchService: Handling description collection in context: '${event.text}'" }
                    processJobSearchDescription(event.chatId, event.userId, event.text)
                }
                
                event.commandName == null && currentContext is SearchNowSubContext.ConfirmingDetails -> {
                    logger.info { "🔍 ImmediateSearchService: Handling confirmation in context: '${event.text}'" }
                    processConfirmation(event.chatId, event.userId, event.username, event.text)
                }
                
                // Handle /cancel command
                event.commandName == "/cancel" && currentContext is SearchNowSubContext -> {
                    logger.info { "🔍 ImmediateSearchService: Processing /cancel command" }
                    sendMessage(event.chatId, Messages.CANCEL_MESSAGE)
                    sessionManager.resetToIdle(event.userId)
                }
                
                else -> {
                    logger.debug { "🔍 ImmediateSearchService: Event not handled - commandName='${event.commandName}', context=$currentContext" }
                }
            }
        }
    }

    private suspend fun processInitial(event: TelegramMessageReceived) {
        sendMessage(event.chatId, Messages.getImmediateSearchInstructions())
        sessionManager.setContext(chatId = event.chatId, userId = event.userId, context = SearchNowSubContext.CollectingDescription)
    }

    private suspend fun processJobSearchDescription(chatId: Long, userId: Long, description: String) {
        try {
            // Check daily search limits BEFORE parsing
            val limitCheck = userLimitsService.checkDailySearchLimit(userId)
            if (!limitCheck.allowed) {
                sendMessage(chatId, Messages.getDailySearchLimitExceededMessage(limitCheck))
                sessionManager.resetToIdle(userId)
                return
            }

            sendMessage(chatId, Messages.ANALYZING_SEARCH)

            val parseResult = jobSearchParserService.parseUserInput(description, userId)

            if (parseResult.success && parseResult.jobSearchIn != null) {
                // Successfully parsed, show for confirmation
                // Override timePeriod for immediate searches
                val immediateJobSearch = parseResult.jobSearchIn.copy(timePeriod = TimePeriod.getOneTimeSearchPeriod())
                
                sessionManager.updateSession(userId) { session ->
                    session.copy(
                        pendingJobSearch = immediateJobSearch,
                        retryCount = 0
                    )
                }
                sessionManager.setContext(chatId = chatId, userId = userId, context = SearchNowSubContext.ConfirmingDetails)
                
                sendMessage(chatId, Messages.getSearchConfirmation(immediateJobSearch))
            } else {
                // Parsing failed, ask for retry
                handleParseFailure(chatId, userId, parseResult)
            }
        } catch (e: Exception) {
            logger.error(e) { "Error processing job search description for user $userId" }
            sendMessage(chatId, Messages.ERROR_GENERAL)
        }
    }

    private suspend fun processConfirmation(chatId: Long, userId: Long, username: String?, confirmation: String) {
        val session = sessionManager.getSession(userId, chatId, username)
        val jobSearch = session.pendingJobSearch

        if (jobSearch == null) {
            sendMessage(chatId, Messages.ERROR_NO_PENDING_SEARCH)
            sessionManager.resetToIdle(userId)
            return
        }

        val lowerConfirmation = confirmation.lowercase().trim()

        when {
            lowerConfirmation in listOf("yes", "y", "confirm", "ok", "proceed") -> {
                try {
                    // Track the search usage BEFORE performing the search
                    userLimitsService.trackDailySearch(userId)
                    
                    sendMessage(chatId, Messages.STARTING_SEARCH)

                    val searchId = performImmediateSearch(jobSearch)
                    sendMessage(chatId, Messages.getSearchInitiatedSuccess(searchId, jobSearch))
                    sessionManager.resetToIdle(userId)
                } catch (e: Exception) {
                    logger.error(e) { "Error performing immediate search for user $userId" }
                    sendMessage(chatId, Messages.ERROR_CREATION_FAILED)
                    sessionManager.resetToIdle(userId)
                }
            }
            lowerConfirmation in listOf("no", "n", "cancel", "modify", "change") -> {
                sendMessage(chatId, Messages.getRetryJobSearchMessage())
                sessionManager.setContext(chatId = chatId, userId = userId, context = SearchNowSubContext.CollectingDescription)
                sessionManager.updateSession(userId) { session ->
                    session.copy(
                        pendingJobSearch = null,
                        retryCount = session.retryCount + 1
                    )
                }
            }
            else -> {
                sendMessage(chatId, Messages.getConfirmationInstruction("search"))
            }
        }
    }

    private suspend fun performImmediateSearch(jobSearch: JobSearchIn): String {
        val jobSearchId = "temp-${System.currentTimeMillis()}"
        
        // Convert to JobSearchOut for processing
        val jobSearchOut = JobSearchOut.fromJobSearchIn(jobSearch).copy(id = jobSearchId)
        
        // Trigger immediate search
        scraperJobService.triggerScraperJobAndLog(jobSearchOut)
        
        return jobSearchId
    }

    private suspend fun handleParseFailure(chatId: Long, userId: Long, parseResult: JobSearchParseResult) {
        val session = sessionManager.getSession(userId, chatId, "")
        val newRetryCount = session.retryCount + 1

        if (newRetryCount >= 3) {
            sendMessage(chatId, Messages.getStructuredApproachMessage())
            sessionManager.updateSession(userId) { session ->
                session.copy(retryCount = newRetryCount)
            }
        } else {
            sendMessage(chatId, Messages.getParseErrorMessage(parseResult))
            sessionManager.updateSession(userId) { session ->
                session.copy(retryCount = newRetryCount)
            }
        }
    }

    private suspend fun sendMessage(chatId: Long, message: String) {
        toTelegramEventBus.publish(
            ToTelegramSendMessageEvent(
                message = message,
                chatId = chatId,
                eventSource = "ImmediateSearchService"
            )
        )
    }
}  
