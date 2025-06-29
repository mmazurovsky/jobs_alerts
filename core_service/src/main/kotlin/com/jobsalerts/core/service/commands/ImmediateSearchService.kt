package com.jobsalerts.core.service

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
    private val jobSearchService: JobSearchService,
    private val scraperJobService: ScraperJobService,
    private val fromTelegramEventBus: FromTelegramEventBus,
    private val toTelegramEventBus: ToTelegramEventBus,
    private val sessionManager: SessionManager
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

            when {
                // User sent /search_now without parameters -> start flow, show instructions
                event.commandName == "/search_now" && initialDescription.isNullOrEmpty() -> {
                    sessionManager.setContext(event.userId, SearchNowSubContext.Initial)
                    try {
                        processInitial(event)
                    } catch (e: Exception) {
                        logger.error(e) { "Error processing initial search for user ${event.userId}" }
                    }
                }

                // User sent /search_now with a description OR we are in CollectingDescription context
                (event.commandName == "/search_now" && !initialDescription.isNullOrEmpty()) ||
                        currentContext is SearchNowSubContext.CollectingDescription -> {
                    sessionManager.setContext(event.userId, SearchNowSubContext.CollectingDescription)
                    val descriptionToUse = if (!initialDescription.isNullOrEmpty()) initialDescription else event.text
                    try {
                        processJobSearchDescription(event.chatId, event.userId, descriptionToUse)
                    } catch (e: Exception) {
                        logger.error(e) { "Error processing job search description for user ${event.userId}" }
                    }
                }

                // We already parsed and are waiting for confirmation
                currentContext is SearchNowSubContext.ConfirmingDetails -> {
                    processConfirmation(event.chatId, event.userId, event.userName, event.text)
                }

                // User cancelled
                event.commandName == "/cancel" && currentContext is SearchNowSubContext -> {
                    sendMessage(event.chatId, "❌ Immediate search cancelled.")
                    sessionManager.resetToIdle(event.userId)
                }
            }
        }
    }

    private suspend fun processInitial(event: TelegramMessageReceived) {
        val instructionsMessage = buildString {
            appendLine("🔍 **Running an immediate job search**")
            appendLine()
            append(JobSearchIn.getFormattingInstructions())
            appendLine()
            appendLine("💡 **Note:** This is a one-time search that will start executing immediately!")
        }
  
        sendMessage(event.chatId, instructionsMessage)
        sessionManager.setContext(event.userId, SearchNowSubContext.CollectingDescription)
    }

    private suspend fun sendMessage(chatId: Long, message: String) {
        toTelegramEventBus.publish(ToTelegramSendMessageEvent(
            message = message,
            chatId = chatId,
            eventSource = "ImmediateSearchService"
        ))
    }

    private suspend fun triggerImmediateSearch(input: JobSearchIn): String {
        // Create a temporary job search object without saving it to database
        val tempJobSearch = JobSearchOut.fromJobSearchInAsTemp(input)
        
        logger.info { "Triggering immediate search: ${tempJobSearch.toLogString()}" }
        
        try {
            // Trigger the scraper job without saving the search
            scraperJobService.triggerScraperJobAndLog(tempJobSearch)
            logger.info { "Successfully triggered immediate search for user ${input.userId}" }
            return tempJobSearch.id
        } catch (e: Exception) {
            logger.error(e) { "Failed to trigger immediate search: ${tempJobSearch.toLogString()}" }
            throw e
        }
    }

    private suspend fun processJobSearchDescription(
        chatId: Long,
        userId: Long,
        description: String
    ) {
        try {
            sendMessage(chatId, "🔍 Analyzing your job search description...")
            
            val parseResult = jobSearchParserService.parseUserInput(description, userId.toInt())
            
            if (parseResult.success && parseResult.jobSearchIn != null) {
                // Successfully parsed, show for confirmation
                val confirmationMessage = buildString {
                    appendLine("✅ **Job search parsed successfully!**")
                    appendLine()
                    append(parseResult.jobSearchIn.toHumanReadableString())
                    appendLine()
                    appendLine("**Is this correct?**")
                    appendLine("• Reply '**yes**' to proceed with the search")
                    appendLine("• Reply '**no**' to modify your search")
                    appendLine("• Use /cancel to abort")
                }
                
                sessionManager.updateSession(userId) { session ->
                    session.copy(
                        pendingJobSearch = parseResult.jobSearchIn,
                        retryCount = 0
                    )
                }
                sessionManager.setContext(userId, SearchNowSubContext.ConfirmingDetails)
                
                sendMessage(chatId, confirmationMessage)
            } else {
                // Parsing failed, ask for retry
                handleParseFailure(chatId, userId, parseResult)
            }
        } catch (e: Exception) {
            logger.error(e) { "Error processing job search description for user $userId" }
            sendMessage(chatId, "❌ An error occurred while processing your request. Please try again or use /cancel to abort.")
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
            sendMessage(chatId, "❌ No pending job search found. Please start over with /search_now")
            sessionManager.resetToIdle(userId)
            return
        }

        val lowerConfirmation = confirmation.lowercase().trim()
        
        when {
            lowerConfirmation in listOf("yes", "y", "confirm", "ok", "proceed") -> {
                try {
                    sendMessage(chatId, "🚀 **Starting your job search...**")
                    
                    val searchId = triggerImmediateSearch(jobSearch)
                    
                    val successMessage = buildString {
                        appendLine("✅ **Job search initiated successfully!**")
                        appendLine()
                        appendLine("📋 **Search ID:** $searchId")
                        appendLine("🔍 **Searching for:** ${jobSearch.jobTitle}")
                        appendLine("📍 **Location:** ${jobSearch.location}")
                        appendLine()
                        appendLine("⏳ Your job search is now running. Results will be sent to you once the search is complete in few minutes.")
                        appendLine()
                        appendLine("Use /menu to access other options.")
                    }
                    
                    sendMessage(chatId, successMessage)
                    sessionManager.resetToIdle(userId)
                    
                } catch (e: Exception) {
                    logger.error(e) { "Error triggering immediate search for user $userId" }
                    sendMessage(chatId, "❌ Failed to start job search. Please try again later or contact support.")
                    sessionManager.resetToIdle(userId)
                }
            }
            
            lowerConfirmation in listOf("no", "n", "cancel", "modify", "change") -> {
                val retryMessage = buildString {
                    appendLine("📝 **Let's modify your job search.**")
                    appendLine()
                    append(JobSearchIn.getFormattingInstructions())
                }
                
                sessionManager.setContext(userId, SearchNowSubContext.CollectingDescription)
                sessionManager.updateSession(userId) { session ->
                    session.copy(
                        pendingJobSearch = null,
                        retryCount = session.retryCount + 1
                    )
                }
                
                sendMessage(chatId, retryMessage)
            }
            
            else -> {
                sendMessage(chatId, "Please respond with '**yes**' to proceed, '**no**' to modify, or /cancel to abort.")
            }
        }
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
                appendLine("❌ **I'm having trouble understanding your job search description.**")
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
                    appendLine("**Missing information:** ${parseResult.missingFields.joinToString(", ")}")
                    appendLine()
                }
                appendLine("Please try again with a clearer description:")
                appendLine()
                appendLine("**Examples:**")
                appendLine("• \"Senior Software Engineer in San Francisco, full-time, remote\"")
                appendLine("• \"Data Scientist role in Berlin, contract work preferred\"")
                appendLine("• \"Product Manager in New York, full-time, on-site only\"")
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