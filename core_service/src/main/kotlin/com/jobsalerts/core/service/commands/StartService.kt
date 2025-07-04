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
class StartService(
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
        logger.info { "StartService initialized and subscribed to events" }
    }

    @PreDestroy
    fun cleanup() {
        eventSubscription?.cancel()
        serviceScope.cancel()
        logger.info { "StartService cleanup completed" }
    }

    private suspend fun handleEvent(event: FromTelegramEvent) {
        if (event is TelegramMessageReceived) {
            val currentContext = sessionManager.getCurrentContext(event.userId)
            
            when {
                event.commandName == "/start" -> {
                    logger.info { "🚀 StartService: Processing /start command for user ${event.userId}" }
                    sessionManager.setContext(chatId = event.chatId, userId = event.userId, context = StartSubContext.ShowingWelcome)
                    try {
                        processStartRequest(event.chatId, event.userId)
                        logger.info { "✅ StartService: Successfully processed /start command" }
                    } catch (e: Exception) {
                        logger.error(e) { "💥 StartService: Error processing start request for user ${event.userId}" }
                        sendMessage(event.chatId, Messages.ERROR_DISPLAY_WELCOME)
                        sessionManager.resetToIdle(event.userId)
                    }
                }
                
                event.commandName == "/menu" -> {
                    logger.info { "📋 StartService: Processing /menu command for user ${event.userId}" }
                    sessionManager.setContext(chatId = event.chatId, userId = event.userId, context = StartSubContext.ShowingWelcome)
                    try {
                        processMenuRequest(event.chatId, event.userId)
                        logger.info { "✅ StartService: Successfully processed /menu command" }
                    } catch (e: Exception) {
                        logger.error(e) { "💥 StartService: Error processing menu request for user ${event.userId}" }
                        sendMessage(event.chatId, Messages.ERROR_DISPLAY_MENU)
                        sessionManager.resetToIdle(event.userId)
                    }
                }
                
                event.commandName == "/cancel" && currentContext is StartSubContext -> {
                    logger.info { "❌ StartService: Processing /cancel command for user ${event.userId}" }
                    sendMessage(event.chatId, Messages.CANCEL_MESSAGE)
                    sessionManager.resetToIdle(event.userId)
                }
                
                // Only log if this service should handle the event
                event.commandName in listOf("/start", "/menu") || 
                (event.commandName == "/cancel" && currentContext is StartSubContext) -> {
                    logger.debug { "🔇 StartService: Handled relevant event but no action taken" }
                }
            }
        }
    }

    private suspend fun processStartRequest(chatId: Long, userId: Long) {
        // Reset user session to idle context
        sessionManager.resetToIdle(userId)
        
        try {
            sendMessage(chatId, Messages.getWelcomeMessage())
            // Reset to idle after showing welcome
            sessionManager.resetToIdle(userId)
        } catch (e: Exception) {
            logger.error(e) { "Error sending welcome message to user $userId" }
            sendMessage(chatId, Messages.ERROR_DISPLAY_WELCOME)
            sessionManager.resetToIdle(userId)
        }
    }

    private suspend fun processMenuRequest(chatId: Long, userId: Long) {
        // Reset user session to idle context
        sessionManager.resetToIdle(userId)
        
        try {
            sendMessage(chatId, Messages.getMainMenuMessage())
            // Reset to idle after showing menu
            sessionManager.resetToIdle(userId)
        } catch (e: Exception) {
            logger.error(e) { "Error sending menu message to user $userId" }
            sendMessage(chatId, Messages.ERROR_DISPLAY_MENU)
            sessionManager.resetToIdle(userId)
        }
    }

    private suspend fun sendMessage(chatId: Long, message: String) {
        toTelegramEventBus.publish(
            ToTelegramSendMessageEvent(
                message = message,
                chatId = chatId,
                eventSource = "StartService"
            )
        )
    }
} 