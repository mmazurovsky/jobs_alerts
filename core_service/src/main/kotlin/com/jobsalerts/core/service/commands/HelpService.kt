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
class HelpService(
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
        logger.info { "HelpService initialized and subscribed to events" }
    }

    @PreDestroy
    fun cleanup() {
        eventSubscription?.cancel()
        serviceScope.cancel()
        logger.info { "HelpService cleanup completed" }
    }

    private suspend fun handleEvent(event: FromTelegramEvent) {
        if (event is TelegramMessageReceived) {
            val currentContext = sessionManager.getCurrentContext(event.userId)
            
            when {
                event.commandName == "/help" -> {
                    logger.info { "📖 HelpService: Processing /help command for user ${event.userId}" }
                    sessionManager.setContext(chatId = event.chatId, userId = event.userId, context = HelpSubContext.ShowingHelp)
                    try {
                        processHelpRequest(event.chatId, event.userId)
                        logger.info { "✅ HelpService: Successfully processed /help command" }
                    } catch (e: Exception) {
                        logger.error(e) { "💥 HelpService: Error processing help request for user ${event.userId}" }
                        sendMessage(event.chatId, Messages.ERROR_DISPLAY_HELP)
                        sessionManager.resetToIdle(event.userId)
                    }
                }
                
                event.commandName == "/cancel" && currentContext is HelpSubContext -> {
                    logger.info { "❌ HelpService: Processing /cancel command for user ${event.userId}" }
                    sendMessage(event.chatId, Messages.CANCEL_MESSAGE)
                    sessionManager.resetToIdle(event.userId)
                }
                
                // Only log if this service should handle the event  
                event.commandName == "/help" || 
                (event.commandName == "/cancel" && currentContext is HelpSubContext) -> {
                    logger.debug { "🔇 HelpService: Handled relevant event but no action taken" }
                }
            }
        }
    }

    private suspend fun processHelpRequest(chatId: Long, userId: Long) {
        try {
            sendMessage(chatId, Messages.getHelpMessage())
            // Reset to idle after showing help
            sessionManager.resetToIdle(userId)
        } catch (e: Exception) {
            logger.error(e) { "Error sending help message to user $userId" }
            sendMessage(chatId, Messages.ERROR_DISPLAY_HELP)
            sessionManager.resetToIdle(userId)
        }
    }

    private suspend fun sendMessage(chatId: Long, message: String) {
        toTelegramEventBus.publish(
            ToTelegramSendMessageEvent(
                message = message,
                chatId = chatId,
                eventSource = "HelpService"
            )
        )
    }
} 