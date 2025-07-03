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
class ListSearchesService(
    private val fromTelegramEventBus: FromTelegramEventBus,
    private val toTelegramEventBus: ToTelegramEventBus,
    private val sessionManager: SessionManager,
    private val jobSearchRepository: JobSearchRepository
) : Logging {

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var eventSubscription: Job? = null

    @PostConstruct
    fun initialize() {
        eventSubscription = fromTelegramEventBus.subscribe(serviceScope) { event ->
            handleEvent(event)
        }
        logger.info { "ListSearchesService initialized and subscribed to events" }
    }

    @PreDestroy
    fun cleanup() {
        eventSubscription?.cancel()
        serviceScope.cancel()
        logger.info { "ListSearchesService cleanup completed" }
    }

    private suspend fun handleEvent(event: FromTelegramEvent) {
        if (event is TelegramMessageReceived) {
            val currentContext = sessionManager.getCurrentContext(event.userId)
            
            when {
                event.commandName == "/list_alerts" -> {
                    sessionManager.setContext(chatId = event.chatId, userId = event.userId, context = ListAlertsSubContext.ViewingList)
                    try {
                        processListRequest(event.chatId, event.userId)
                    } catch (e: Exception) {
                        logger.error(e) { "Error processing list request for user ${event.userId}" }
                        sendMessage(event.chatId, Messages.ERROR_RETRIEVAL)
                        sessionManager.resetToIdle(event.userId)
                    }
                }
                
                event.commandName == "/cancel" && currentContext is ListAlertsSubContext -> {
                    sendMessage(event.chatId, Messages.CANCEL_MESSAGE)
                    sessionManager.resetToIdle(event.userId)
                }
            }
        }
    }

    private suspend fun processListRequest(chatId: Long, userId: Long) {
        val userSearches = jobSearchRepository.findByUserId(userId)
        
        if (userSearches.isEmpty()) {
            sendMessage(chatId, Messages.getNoActiveAlertsMessage())
        } else {
            sendMessage(chatId, Messages.getActiveAlertsMessage(userSearches))
        }
        
        // Reset to idle after showing the list
        sessionManager.resetToIdle(userId)
    }

    private suspend fun sendMessage(chatId: Long, message: String) {
        toTelegramEventBus.publish(
            ToTelegramSendMessageEvent(
                message = message,
                chatId = chatId,
                eventSource = "ListSearchesService"
            )
        )
    }
} 