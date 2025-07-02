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
                        sendMessage(event.chatId, "❌ Error displaying welcome message. Please try again later.")
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
                        sendMessage(event.chatId, "❌ Error displaying menu. Please try again later.")
                        sessionManager.resetToIdle(event.userId)
                    }
                }
                
                event.commandName == "/cancel" && currentContext is StartSubContext -> {
                    logger.info { "❌ StartService: Processing /cancel command for user ${event.userId}" }
                    sendMessage(event.chatId, "❌ Operation cancelled.")
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
        
        val welcomeMessage = """
            🤖 **Welcome to Job Alerts Bot!**
            
            I'll help you stay updated with the latest job opportunities matching your preferences.
            
            Use the commands below to get started:
            
            📋 **Available Commands:**
            /menu - Show main menu
            /create_alert - Create a new job search alert
            /search_now - Run an immediate job search
            /list_alerts - View your active job alerts
            /edit_alert - Modify existing job alerts
            /delete_alert - Remove job alerts
            /help - Show detailed help
            /cancel - Cancel current operation
            
            **Getting Started:**
            1. 🔔 Create your first alert with /create_alert
            2. 🔍 Or try an immediate search with /search_now
            3. 📖 Need help? Use /help for detailed instructions
            
            Type any command or use /menu to see options!
        """.trimIndent()

        try {
            sendMessage(chatId, welcomeMessage)
            // Reset to idle after showing welcome
            sessionManager.resetToIdle(userId)
        } catch (e: Exception) {
            logger.error(e) { "Error sending welcome message to user $userId" }
            sendMessage(chatId, "❌ Error displaying welcome message. Please try again later.")
            sessionManager.resetToIdle(userId)
        }
    }

    private suspend fun processMenuRequest(chatId: Long, userId: Long) {
        // Reset user session to idle context
        sessionManager.resetToIdle(userId)
        
        val menuMessage = """
            📋 **Main Menu**
            
            Choose what you'd like to do:
            
            **Job Alert Management:**
            /create_alert - 🔔 Create new job alert
            /list_alerts - 📋 View your alerts
            /edit_alert - ✏️ Edit an alert
            /delete_alert - 🗑️ Delete an alert
            
            **Search Jobs:**
            /search_now - 🔍 Search jobs immediately
            
            **Help & Info:**
            /help - 📖 Detailed help
            /start - 🏠 Welcome message
            
            **Tips:**
            • You can add parameters to commands (e.g., /edit_alert 123)
            • Use natural language when describing job requirements
            • All searches are powered by AI for better matching
            
            Just type any command to get started!
        """.trimIndent()

        try {
            sendMessage(chatId, menuMessage)
            // Reset to idle after showing menu
            sessionManager.resetToIdle(userId)
        } catch (e: Exception) {
            logger.error(e) { "Error sending menu message to user $userId" }
            sendMessage(chatId, "❌ Error displaying menu. Please try again later.")
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