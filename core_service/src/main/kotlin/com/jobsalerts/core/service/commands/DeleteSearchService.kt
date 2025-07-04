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
class DeleteSearchService(
    private val fromTelegramEventBus: FromTelegramEventBus,
    private val toTelegramEventBus: ToTelegramEventBus,
    private val sessionManager: SessionManager,
    private val jobSearchRepository: JobSearchRepository,
    private val jobSearchScheduler: JobSearchScheduler
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
            
            logger.info { "🗑️ DeleteSearchService: Processing event - commandName='${event.commandName}', context=$currentContext, userId=${event.userId}" }
            
            when {
                // Handle /delete_alert commands
                event.commandName == "/delete_alert" && alertIds.isNullOrEmpty() -> {
                    logger.info { "🗑️ DeleteSearchService: Processing /delete_alert command (no parameters)" }
                    sessionManager.setContext(chatId = event.chatId, userId = event.userId, context = DeleteAlertSubContext.SelectingAlert)
                    logger.info { "🗑️ DeleteSearchService: Context set to SelectingAlert for user ${event.userId}" }
                    try {
                        processInitialDelete(event.chatId, event.userId)
                    } catch (e: Exception) {
                        logger.error(e) { "Error processing initial delete for user ${event.userId}" }
                        sendMessage(event.chatId, Messages.ERROR_RETRIEVAL)
                        sessionManager.resetToIdle(event.userId)
                    }
                }
                event.commandName == "/delete_alert" && !alertIds.isNullOrEmpty() -> {
                    logger.info { "🗑️ DeleteSearchService: Processing /delete_alert command with parameters: $alertIds" }
                    sessionManager.setContext(chatId = event.chatId, userId = event.userId, context = DeleteAlertSubContext.SelectingAlert)
                    processAlertIdProvided(event.chatId, event.userId, alertIds)
                }
                
                // Handle context-based plain text messages (alert ID selection)
                event.commandName == null && currentContext is DeleteAlertSubContext.SelectingAlert -> {
                    logger.info { "🗑️ DeleteSearchService: Handling alert ID selection in context: '${event.text}'" }
                    processAlertIdSelection(event.chatId, event.userId, event.text)
                }
                
                // Handle confirmation messages
                event.commandName == null && currentContext is DeleteAlertSubContext.ConfirmingDeletion -> {
                    logger.info { "🗑️ DeleteSearchService: Handling deletion confirmation in context: '${event.text}'" }
                    processConfirmationRequest(event.chatId, event.userId, event.text)
                }
                
                // Handle /cancel command
                event.commandName == "/cancel" && currentContext is DeleteAlertSubContext -> {
                    logger.info { "🗑️ DeleteSearchService: Processing /cancel command" }
                    sendMessage(event.chatId, Messages.CANCEL_MESSAGE)
                    sessionManager.resetToIdle(event.userId)
                }
                
                else -> {
                    logger.debug { "🗑️ DeleteSearchService: Event not handled - commandName='${event.commandName}', context=$currentContext" }
                }
            }
        }
    }

    private suspend fun processInitialDelete(chatId: Long, userId: Long) {
        val userSearches = jobSearchRepository.findByUserId(userId)
        
        if (userSearches.isEmpty()) {
            sendMessage(chatId, Messages.getNoAlertsToDeleteMessage())
            sessionManager.resetToIdle(userId)
            return
        }
        
        sendMessage(chatId, Messages.getSelectAlertToDeleteMessage(userSearches))
    }

    private suspend fun processAlertIdProvided(chatId: Long, userId: Long, alertIds: String) {
        val alertIdList = alertIds.split(",").map { it.trim() }.filter { it.isNotEmpty() }
        val userSearches = jobSearchRepository.findByUserId(userId)
        val validAlertIds = alertIdList.filter { alertId ->
            userSearches.any { it.id == alertId }
        }
        val invalidAlertIds = alertIdList - validAlertIds.toSet()

        if (invalidAlertIds.isNotEmpty()) {
            sendMessage(chatId, Messages.getInvalidAlertIdsMessage(invalidAlertIds, validAlertIds))
            
            // Go back to selecting alert if no valid IDs
            if (validAlertIds.isEmpty()) {
                sessionManager.setContext(chatId = chatId, userId = userId, context = DeleteAlertSubContext.SelectingAlert)
            }
            return
        }

        // Store selected alert IDs and proceed to confirmation
        sessionManager.updateSession(userId) { session ->
            session.copy(selectedAlertId = alertIds)
        }
        sessionManager.setContext(chatId = chatId, userId = userId, context = DeleteAlertSubContext.ConfirmingDeletion)
        
        sendMessage(chatId, Messages.getDeleteConfirmationMessage(validAlertIds))
    }

    private suspend fun processAlertIdSelection(chatId: Long, userId: Long, alertIds: String) {
        processAlertIdProvided(chatId, userId, alertIds)
    }

    private suspend fun processConfirmationRequest(chatId: Long, userId: Long, confirmation: String) {
        val session = sessionManager.getSession(userId, chatId, "")
        val selectedAlertIds = session.selectedAlertId
        
        if (selectedAlertIds.isNullOrEmpty()) {
            sendMessage(chatId, Messages.ERROR_NO_PENDING_ALERT)
            sessionManager.resetToIdle(userId)
            return
        }
        
        val lowerConfirmation = confirmation.lowercase().trim()
        
        when {
            lowerConfirmation in listOf("yes", "y", "confirm", "ok", "proceed") -> {
                performDeletion(chatId, userId, selectedAlertIds)
            }
            lowerConfirmation in listOf("no", "n", "cancel") -> {
                sendMessage(chatId, Messages.CANCEL_MESSAGE)
                sessionManager.setContext(userId, userId = userId, context = DeleteAlertSubContext.SelectingAlert)
            }
            else -> {
                sendMessage(chatId, Messages.getConfirmationInstruction("delete"))
            }
        }
    }

    private suspend fun performDeletion(chatId: Long, userId: Long, selectedAlertIds: String) {
        val alertIdList = selectedAlertIds.split(",").map { it.trim() }.filter { it.isNotEmpty() }
        val deletedIds = mutableListOf<String>()
        val failedIds = mutableListOf<String>()
        
        alertIdList.forEach { alertId ->
            try {
                val deleted = jobSearchRepository.deleteByIdAndUserId(alertId, userId)
                if (deleted > 0) {
                    jobSearchScheduler.removeJobSearch(alertId)
                    deletedIds.add(alertId)
                    logger.info { "Deleted job search: $alertId for user $userId" }
                } else {
                    failedIds.add(alertId)
                    logger.warn { "Failed to delete job search: $alertId for user $userId - not found" }
                }
            } catch (e: Exception) {
                logger.error(e) { "Error deleting job search: $alertId for user $userId" }
                failedIds.add(alertId)
            }
        }
        
        sendMessage(chatId, Messages.getDeletionResultMessage(deletedIds, failedIds))
        sessionManager.resetToIdle(userId)
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