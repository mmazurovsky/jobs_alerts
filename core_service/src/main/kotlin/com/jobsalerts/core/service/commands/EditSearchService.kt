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
class EditSearchService(
    private val jobSearchService: JobSearchService,
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
        eventSubscription = fromTelegramEventBus.subscribe(serviceScope) { event ->
            handleEvent(event)
        }
        logger.info { "EditSearchService initialized and subscribed to events" }
    }

    @PreDestroy
    fun cleanup() {
        eventSubscription?.cancel()
        serviceScope.cancel()
        logger.info { "EditSearchService cleanup completed" }
    }

    private suspend fun handleEvent(event: FromTelegramEvent) {
        if (event is TelegramMessageReceived) {
            val currentContext = sessionManager.getCurrentContext(event.userId)
            val alertId = event.commandParameters?.trim()
            
            when {
                // Handle /edit_alert commands
                event.commandName == "/edit_alert" && alertId.isNullOrEmpty() -> {
                    logger.info { "✏️ EditSearchService: Processing /edit_alert command (no parameters)" }
                    sessionManager.setContext(chatId = event.chatId, userId = event.userId, context = EditAlertSubContext.SelectingAlert)
                    try {
                        processInitialEdit(event.chatId, event.userId)
                    } catch (e: Exception) {
                        logger.error(e) { "Error processing initial edit for user ${event.userId}" }
                        sendMessage(event.chatId, "❌ Error retrieving your job alerts. Please try again later.")
                        sessionManager.resetToIdle(event.userId)
                    }
                }
                
                event.commandName == "/edit_alert" && !alertId.isNullOrEmpty() -> {
                    logger.info { "✏️ EditSearchService: Processing /edit_alert command with parameters: $alertId" }
                    sessionManager.setContext(chatId = event.chatId, userId = event.userId, context = EditAlertSubContext.CollectingChanges)
                    sessionManager.updateSession(event.userId) { session ->
                        session.copy(selectedAlertId = alertId)
                    }
                    try {
                        processAlertIdProvided(event.chatId, event.userId, alertId)
                    } catch (e: Exception) {
                        logger.error(e) { "Error processing edit alert request for user ${event.userId}" }
                        sendMessage(event.chatId, "❌ Error processing edit request. Please try again later.")
                        sessionManager.resetToIdle(event.userId)
                    }
                }
                
                event.commandName == "/cancel" && currentContext is EditAlertSubContext -> {
                    logger.info { "✏️ EditSearchService: Processing /cancel command" }
                    sendMessage(event.chatId, "❌ Edit operation cancelled.")
                    sessionManager.resetToIdle(event.userId)
                }
                
                // Handle context-based plain text messages
                event.commandName == null && currentContext is EditAlertSubContext.SelectingAlert -> {
                    logger.info { "✏️ EditSearchService: Handling alert selection in context: '${event.text}'" }
                    processAlertIdSelection(event.chatId, event.userId, event.text)
                }
                
                event.commandName == null && currentContext is EditAlertSubContext.CollectingChanges -> {
                    logger.info { "✏️ EditSearchService: Handling job search changes in context: '${event.text}'" }
                    processJobSearchChanges(event.chatId, event.userId, event.text)
                }
                
                event.commandName == null && currentContext is EditAlertSubContext.ConfirmingChanges -> {
                    logger.info { "✏️ EditSearchService: Handling confirmation in context: '${event.text}'" }
                    processConfirmation(event.chatId, event.userId, event.text)
                }
            }
        }
    }

    private suspend fun processInitialEdit(chatId: Long, userId: Long) {
        try {
            val userSearches = jobSearchService.getUserSearches(userId)
            
            if (userSearches.isEmpty()) {
                val message = """
                    ✏️ **Edit Job Alert**
                    
                    You don't have any active job alerts to edit.
                    
                    **Get started:**
                    /create_alert - Create your first job alert
                    /help - See all available commands
                """.trimIndent()
                
                sendMessage(chatId, message)
                sessionManager.resetToIdle(userId)
            } else {
                val message = buildString {
                    appendLine("✏️ **Edit Job Alert**")
                    appendLine()
                    appendLine("Which alert would you like to edit? Please provide the alert ID.")
                    appendLine()
                    appendLine("**Your Active Job Alerts:**")
                    appendLine()
                    
                    userSearches.forEach { jobSearch ->
                        append(jobSearch.toMessage())
                        appendLine("─".repeat(40))
                        appendLine()
                    }
                    
                    appendLine("**Example:** `123` (just the ID number)")
                    appendLine()
                    appendLine("Use /cancel to abort this operation.")
                }
                
                sendMessage(chatId, message.toString())
            }
        } catch (e: Exception) {
            logger.error(e) { "Error in processInitialEdit for user $userId" }
            sendMessage(chatId, "❌ Error retrieving your job alerts. Please try again later.")
            sessionManager.resetToIdle(userId)
        }
    }

    private suspend fun processAlertIdSelection(chatId: Long, userId: Long, text: String) {
        val alertId = text.trim()
        
        if (alertId.isBlank()) {
            sendMessage(chatId, "Please provide a valid alert ID. Use /list_alerts to see your alerts or /cancel to abort.")
            return
        }
        
        sessionManager.updateSession(userId) { session ->
            session.copy(selectedAlertId = alertId)
        }
        sessionManager.setContext(chatId = chatId, userId = userId, context = EditAlertSubContext.CollectingChanges)
        
        processAlertIdProvided(chatId, userId, alertId)
    }

    private suspend fun processAlertIdProvided(chatId: Long, userId: Long, alertId: String) {
        try {
            // Validate that the alert exists and belongs to the user
            val userSearches = jobSearchService.getUserSearches(userId)
            val existingAlert = userSearches.find { it.id == alertId }
            
            if (existingAlert == null) {
                val message = buildString {
                    appendLine("❌ **Invalid Alert ID**")
                    appendLine()
                    appendLine("Alert ID '$alertId' doesn't exist or doesn't belong to you.")
                    appendLine()
                    appendLine("Please provide a valid alert ID or use /list_alerts to see your alerts.")
                }
                sendMessage(chatId, message.toString())
                sessionManager.setContext(chatId = chatId, userId = userId, context = EditAlertSubContext.SelectingAlert)
                return
            }
            
            // Show current alert details and ask for new criteria
            val message = buildString {
                appendLine("✏️ **Editing Alert: $alertId**")
                appendLine()
                appendLine("**Current Alert Details:**")
                appendLine()
                append(existingAlert.toMessage())
                appendLine("─".repeat(40))
                appendLine()
                appendLine("Please provide the new job search criteria:")
                appendLine()
                append(JobSearchIn.getFormattingInstructions())
                appendLine()
                appendLine("Use /cancel to abort this operation.")
            }
            
            sendMessage(chatId, message.toString())
            
        } catch (e: Exception) {
            logger.error(e) { "Error in processAlertIdProvided for user $userId" }
            sendMessage(chatId, "❌ Error processing alert details. Please try again later.")
            sessionManager.resetToIdle(userId)
        }
    }

    private suspend fun processJobSearchChanges(chatId: Long, userId: Long, description: String) {
        try {
            sendMessage(chatId, "🔍 Analyzing your updated job search criteria...")
            
                            val parseResult = jobSearchParserService.parseUserInput(description, userId)
            
            if (parseResult.success && parseResult.jobSearchIn != null) {
                // Successfully parsed, show for confirmation
                val session = sessionManager.getSession(userId, chatId, null)
                val alertId = session.selectedAlertId
                
                val confirmationMessage = buildString {
                    appendLine("✅ **Updated job search parsed successfully!**")
                    appendLine()
                    appendLine("**Alert ID:** $alertId")
                    appendLine()
                    append(parseResult.jobSearchIn.toHumanReadableString())
                    appendLine()
                    appendLine("⏰ **Alert Frequency:** ${parseResult.jobSearchIn.timePeriod.displayName}")
                    appendLine()
                    appendLine("**Is this correct?**")
                    appendLine("• Reply '**yes**' to save the changes")
                    appendLine("• Reply '**no**' to modify your criteria")
                    appendLine("• Use /cancel to abort")
                }
                
                sessionManager.updateSession(userId) { session ->
                    session.copy(pendingJobSearch = parseResult.jobSearchIn, retryCount = 0)
                }
                sessionManager.setContext(chatId = chatId, userId = userId, context = EditAlertSubContext.ConfirmingChanges)
                
                sendMessage(chatId, confirmationMessage)
            } else {
                // Parsing failed, ask for retry
                handleParseFailure(chatId, userId, parseResult)
            }
        } catch (e: Exception) {
            logger.error(e) { "Error processing job search changes for user $userId" }
            sendMessage(chatId, "❌ An error occurred while processing your request. Please try again or use /cancel to abort.")
        }
    }

    private suspend fun processConfirmation(chatId: Long, userId: Long, confirmation: String) {
        val session = sessionManager.getSession(userId, chatId, null)
        val updatedJobSearch = session.pendingJobSearch
        val alertId = session.selectedAlertId
        
        if (updatedJobSearch == null || alertId.isNullOrBlank()) {
            sendMessage(chatId, "❌ No pending changes found. Please start over with /edit_alert")
            sessionManager.resetToIdle(userId)
            return
        }
        
        val lowerConfirmation = confirmation.lowercase().trim()
        
        when {
            lowerConfirmation in listOf("yes", "y", "confirm", "ok", "proceed") -> {
                try {
                    sendMessage(chatId, "✏️ **Updating your job alert...**")
                    
                    // Create updated JobSearchOut from the parsed input
                    val updatedAlert = JobSearchOut.fromJobSearchIn(updatedJobSearch).copy(id = alertId)
                    
                    // Save to database
                    jobSearchRepository.save(updatedAlert)
                    
                    // Update scheduler
                    jobSearchScheduler.removeJobSearch(alertId)
                    jobSearchScheduler.addJobSearch(updatedAlert)
                    
                    val successMessage = buildString {
                        appendLine("✅ **Job alert updated successfully!**")
                        appendLine()
                        appendLine("📋 **Alert ID:** $alertId")
                        appendLine("🔍 **Searching for:** ${updatedJobSearch.jobTitle}")
                        appendLine("📍 **Location:** ${updatedJobSearch.location}")
                        appendLine("⏰ **Frequency:** ${updatedJobSearch.timePeriod.displayName}")
                        appendLine()
                        appendLine("🔔 Your updated alert is now active and will search for jobs with the new criteria.")
                        appendLine()
                        appendLine("Use /list_alerts to see all your alerts or /menu for other options.")
                    }
                    
                    sendMessage(chatId, successMessage)
                    sessionManager.resetToIdle(userId)
                    
                } catch (e: Exception) {
                    logger.error(e) { "Error updating job alert for user $userId" }
                    sendMessage(chatId, "❌ Failed to update job alert. Please try again later or contact support.")
                    sessionManager.resetToIdle(userId)
                }
            }
            
            lowerConfirmation in listOf("no", "n", "cancel", "modify", "change") -> {
                val retryMessage = buildString {
                    appendLine("📝 **Let's modify your job search criteria.**")
                    appendLine()
                    append(JobSearchIn.getFormattingInstructions())
                }
                
                sendMessage(chatId, retryMessage.toString())
                sessionManager.setContext(chatId = chatId, userId = userId, context = EditAlertSubContext.CollectingChanges)
            }
            
            else -> {
                sendMessage(chatId, "Please respond with '**yes**' to save the changes, '**no**' to modify, or /cancel to abort.")
            }
        }
    }

    private suspend fun handleParseFailure(chatId: Long, userId: Long, parseResult: JobSearchParseResult) {
        val session = sessionManager.getSession(userId, chatId, null)
        val currentRetryCount = session.retryCount
        
        if (currentRetryCount >= 2) {
            // Max retries reached
            val message = buildString {
                appendLine("❌ **Unable to parse your job search criteria after multiple attempts.**")
                appendLine()
                appendLine("Please ensure you follow the format guidelines:")
                appendLine()
                append(JobSearchIn.getFormattingInstructions())
                appendLine()
                appendLine("Use /cancel to abort this operation or try again with a clearer description.")
            }
            sendMessage(chatId, message.toString())
        } else {
            // Retry with specific guidance
            val retryCount = currentRetryCount + 1
            sessionManager.updateSession(userId) { session ->
                session.copy(retryCount = retryCount)
            }
            
            val message = buildString {
                appendLine("❌ **Unable to parse your job search criteria.** (Attempt $retryCount/3)")
                appendLine()
                if (!parseResult.errorMessage.isNullOrBlank()) {
                    appendLine("**Error:** ${parseResult.errorMessage}")
                    appendLine()
                }
                appendLine("Please try again with a clearer description:")
                appendLine()
                append(JobSearchIn.getFormattingInstructions())
                appendLine()
                appendLine("Use /cancel to abort this operation.")
            }
            sendMessage(chatId, message.toString())
        }
    }

    private suspend fun sendMessage(chatId: Long, message: String) {
        toTelegramEventBus.publish(
            ToTelegramSendMessageEvent(
                message = message,
                chatId = chatId,
                eventSource = "EditSearchService"
            )
        )
    }
} 