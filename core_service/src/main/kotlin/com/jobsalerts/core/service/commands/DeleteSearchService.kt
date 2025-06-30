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
class DeleteSearchService(
    private val jobSearchService: JobSearchService,
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
        logger.info { "DeleteSearchService initialized and subscribed to events" }
    }

    @PreDestroy
    fun cleanup() {
        eventSubscription?.cancel()
        serviceScope.cancel()
        logger.info { "DeleteSearchService cleanup completed" }
    }

    private suspend fun handleEvent(event: FromTelegramEvent) {
        if (event is TelegramMessageReceived) {
            val currentContext = sessionManager.getCurrentContext(event.userId)
            val alertIds = event.commandParameters?.trim()
            
            when {
                event.commandName == "/delete_alert" && alertIds.isNullOrEmpty() -> {
                    sessionManager.setContext(event.userId, DeleteAlertSubContext.SelectingAlert)
                    try {
                        processInitialDelete(event.chatId, event.userId)
                    } catch (e: Exception) {
                        logger.error(e) { "Error processing initial delete for user ${event.userId}" }
                        sendMessage(event.chatId, "❌ Error retrieving your job alerts. Please try again later.")
                        sessionManager.resetToIdle(event.userId)
                    }
                }
                
                event.commandName == "/delete_alert" && !alertIds.isNullOrEmpty() -> {
                    sessionManager.setContext(event.userId, DeleteAlertSubContext.ConfirmingDeletion)
                    sessionManager.updateSession(event.userId) { session ->
                        session.copy(selectedAlertId = alertIds)
                    }
                    try {
                        processConfirmationRequest(event.chatId, event.userId, alertIds)
                    } catch (e: Exception) {
                        logger.error(e) { "Error processing delete confirmation for user ${event.userId}" }
                        sendMessage(event.chatId, "❌ Error processing deletion request. Please try again later.")
                        sessionManager.resetToIdle(event.userId)
                    }
                }
                
                currentContext is DeleteAlertSubContext.SelectingAlert -> {
                    processAlertIdSelection(event.chatId, event.userId, event.text)
                }
                
                currentContext is DeleteAlertSubContext.ConfirmingDeletion -> {
                    processConfirmation(event.chatId, event.userId, event.text)
                }
                
                event.commandName == "/cancel" && currentContext is DeleteAlertSubContext -> {
                    sendMessage(event.chatId, "❌ Delete operation cancelled.")
                    sessionManager.resetToIdle(event.userId)
                }
            }
        }
    }

    private suspend fun processInitialDelete(chatId: Long, userId: Long) {
        try {
            val userSearches = jobSearchService.getUserSearches(userId)
            
            if (userSearches.isEmpty()) {
                val message = """
                    🗑️ **Delete Job Alert**
                    
                    You don't have any active job alerts to delete.
                    
                    **Get started:**
                    /create_alert - Create your first job alert
                    /help - See all available commands
                """.trimIndent()
                
                sendMessage(chatId, message)
                sessionManager.resetToIdle(userId)
            } else {
                val message = buildString {
                    appendLine("🗑️ **Delete Job Alert**")
                    appendLine()
                    appendLine("Which alert(s) would you like to delete? Please provide the alert ID(s).")
                    appendLine()
                    appendLine("**Your Active Job Alerts:**")
                    appendLine()
                    
                    userSearches.forEach { jobSearch ->
                        append(jobSearch.toMessage())
                        appendLine("─".repeat(40))
                        appendLine()
                    }
                    
                    appendLine("**Examples:**")
                    appendLine("• `123` - Delete alert with ID 123")
                    appendLine("• `123,456` - Delete alerts with IDs 123 and 456")
                    appendLine()
                    appendLine("Use /cancel to abort this operation.")
                }
                
                sendMessage(chatId, message.toString())
            }
        } catch (e: Exception) {
            logger.error(e) { "Error in processInitialDelete for user $userId" }
            sendMessage(chatId, "❌ Error retrieving your job alerts. Please try again later.")
            sessionManager.resetToIdle(userId)
        }
    }

    private suspend fun processAlertIdSelection(chatId: Long, userId: Long, text: String) {
        val alertIds = text.trim()
        
        if (alertIds.isBlank()) {
            sendMessage(chatId, "Please provide valid alert ID(s). Use /list_alerts to see your alerts or /cancel to abort.")
            return
        }
        
        sessionManager.updateSession(userId) { session ->
            session.copy(selectedAlertId = alertIds)
        }
        sessionManager.setContext(userId, DeleteAlertSubContext.ConfirmingDeletion)
        
        processConfirmationRequest(chatId, userId, alertIds)
    }

    private suspend fun processConfirmationRequest(chatId: Long, userId: Long, alertIds: String) {
        try {
            val alertIdList = alertIds.split(",").map { it.trim() }.filter { it.isNotBlank() }
            
            // Validate that all alert IDs exist and belong to the user
            val userSearches = jobSearchService.getUserSearches(userId)
            val validAlertIds = mutableListOf<String>()
            val invalidAlertIds = mutableListOf<String>()
            
            alertIdList.forEach { alertId ->
                val search = userSearches.find { it.id == alertId }
                if (search != null) {
                    validAlertIds.add(alertId)
                } else {
                    invalidAlertIds.add(alertId)
                }
            }
            
            if (invalidAlertIds.isNotEmpty()) {
                val message = buildString {
                    appendLine("❌ **Invalid Alert ID(s)**")
                    appendLine()
                    appendLine("The following alert ID(s) don't exist or don't belong to you:")
                    invalidAlertIds.forEach { appendLine("• $it") }
                    appendLine()
                    if (validAlertIds.isNotEmpty()) {
                        appendLine("Valid alert ID(s): ${validAlertIds.joinToString(", ")}")
                        appendLine()
                        appendLine("Please provide only valid alert IDs or use /cancel to abort.")
                    } else {
                        appendLine("Please provide valid alert ID(s) or use /list_alerts to see your alerts.")
                    }
                }
                sendMessage(chatId, message.toString())
                
                // Go back to selecting alert if no valid IDs
                if (validAlertIds.isEmpty()) {
                    sessionManager.setContext(userId, DeleteAlertSubContext.SelectingAlert)
                }
                return
            }
            
            // All IDs are valid, ask for confirmation
            val message = buildString {
                appendLine("🗑️ **Delete Alert Confirmation**")
                appendLine()
                if (validAlertIds.size == 1) {
                    appendLine("Are you sure you want to delete alert: **${validAlertIds[0]}**?")
                } else {
                    appendLine("Are you sure you want to delete these ${validAlertIds.size} alerts?")
                    validAlertIds.forEach { appendLine("• **$it**") }
                }
                appendLine()
                appendLine("⚠️ **Warning:** This action cannot be undone!")
                appendLine()
                appendLine("• Reply '**yes**' to confirm deletion")
                appendLine("• Reply '**no**' to cancel")
                appendLine("• Use /cancel to abort this operation")
            }
            
            sendMessage(chatId, message.toString())
            
        } catch (e: Exception) {
            logger.error(e) { "Error in processConfirmationRequest for user $userId" }
            sendMessage(chatId, "❌ Error processing deletion request. Please try again later.")
            sessionManager.resetToIdle(userId)
        }
    }

    private suspend fun processConfirmation(chatId: Long, userId: Long, confirmation: String) {
        val session = sessionManager.getSession(userId, chatId, null)
        val alertIds = session.selectedAlertId
        
        if (alertIds.isNullOrBlank()) {
            sendMessage(chatId, "❌ No alert IDs found. Please start over with /delete_alert.")
            sessionManager.resetToIdle(userId)
            return
        }
        
        val lowerConfirmation = confirmation.lowercase().trim()
        
        when {
            lowerConfirmation in listOf("yes", "y", "confirm", "delete") -> {
                try {
                    val alertIdList = alertIds.split(",").map { it.trim() }.filter { it.isNotBlank() }
                    val deletedIds = mutableListOf<String>()
                    val failedIds = mutableListOf<String>()
                    
                    alertIdList.forEach { alertId ->
                        val success = jobSearchService.deleteJobSearch(userId, alertId)
                        if (success) {
                            deletedIds.add(alertId)
                        } else {
                            failedIds.add(alertId)
                        }
                    }
                    
                    val message = buildString {
                        if (deletedIds.isNotEmpty()) {
                            if (deletedIds.size == 1) {
                                appendLine("✅ **Alert ${deletedIds[0]} has been deleted successfully.**")
                            } else {
                                appendLine("✅ **${deletedIds.size} alerts have been deleted successfully:**")
                                deletedIds.forEach { appendLine("• $it") }
                            }
                        }
                        
                        if (failedIds.isNotEmpty()) {
                            appendLine()
                            appendLine("❌ **Failed to delete the following alert(s):**")
                            failedIds.forEach { appendLine("• $it") }
                            appendLine("Please try again later or contact support.")
                        }
                    }
                    
                    sendMessage(chatId, message.toString())
                    sessionManager.resetToIdle(userId)
                    
                } catch (e: Exception) {
                    logger.error(e) { "Error deleting alerts for user $userId" }
                    sendMessage(chatId, "❌ Failed to delete alert(s). Please try again later.")
                    sessionManager.resetToIdle(userId)
                }
            }
            
            lowerConfirmation in listOf("no", "n", "cancel") -> {
                if (alertIds.contains(",")) {
                    sendMessage(chatId, "❌ Alert deletion cancelled. Your alerts are safe!")
                } else {
                    sendMessage(chatId, "❌ Alert deletion cancelled. Your alert is safe!")
                }
                sessionManager.resetToIdle(userId)
            }
            
            else -> {
                sendMessage(chatId, "Please respond with '**yes**' to delete the alert(s), '**no**' to cancel, or /cancel to abort.")
            }
        }
    }

    private suspend fun sendMessage(chatId: Long, message: String) {
        toTelegramEventBus.publish(
            ToTelegramSendMessageEvent(
                message = message,
                chatId = chatId,
                eventSource = "DeleteSearchService"
            )
        )
    }
} 