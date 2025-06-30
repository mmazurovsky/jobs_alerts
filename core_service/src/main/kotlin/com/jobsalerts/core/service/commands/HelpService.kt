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
        logger.info { "📚 HelpService: RECEIVED EVENT: $event" }
        
        if (event is TelegramMessageReceived) {
            logger.info { "📨 HelpService: Processing TelegramMessageReceived - commandName='${event.commandName}', userId=${event.userId}" }
            val currentContext = sessionManager.getCurrentContext(event.userId)
            logger.info { "🔄 HelpService: Current user context: $currentContext" }
            
            when {
                event.commandName == "/help" -> {
                    logger.info { "📖 HelpService: Processing /help command for user ${event.userId}" }
                    sessionManager.setContext(event.userId, HelpSubContext.ShowingHelp)
                    try {
                        processHelpRequest(event.chatId, event.userId)
                        logger.info { "✅ HelpService: Successfully processed /help command" }
                    } catch (e: Exception) {
                        logger.error(e) { "💥 HelpService: Error processing help request for user ${event.userId}" }
                        sendMessage(event.chatId, "❌ Error displaying help. Please try again later.")
                        sessionManager.resetToIdle(event.userId)
                    }
                }
                
                event.commandName == "/cancel" && currentContext is HelpSubContext -> {
                    logger.info { "❌ HelpService: Processing /cancel command for user ${event.userId}" }
                    sendMessage(event.chatId, "❌ Help cancelled.")
                    sessionManager.resetToIdle(event.userId)
                }
                
                else -> {
                    logger.debug { "🔇 HelpService: Ignoring event - commandName='${event.commandName}', currentContext=$currentContext" }
                }
            }
        } else {
            logger.debug { "🔇 HelpService: Ignoring non-TelegramMessageReceived event: $event" }
        }
    }

    private suspend fun processHelpRequest(chatId: Long, userId: Long) {
        val helpMessage = """
            📖 **Job Alerts Bot - Help**
            
            **Main Commands:**
            /start - Welcome message and command overview
            /menu - Show main menu with quick options
            /help - Show this help message
            /cancel - Cancel current operation
            
            **Job Alert Management:**
            /create_alert - 🔔 Create a new job search alert
            /list_alerts - 📋 View all your active job alerts
            /edit_alert - ✏️ Modify an existing job alert
            /delete_alert - 🗑️ Remove a job alert
            
            **Job Search:**
            /search_now - 🔍 Run an immediate one-time job search
            
            **How to use:**
            • Simply type the command (e.g., /create_alert)
            • Add parameters if needed (e.g., /edit_alert 123)
            • Follow the prompts for interactive setup
            
            **Examples:**
            • /create_alert - Start creating a new alert
            • /list_alerts - See all your alerts
            • /search_now python berlin - Search for Python jobs in Berlin
            • /delete_alert 123 - Delete alert with ID 123
            
            **Job Search Format:**
            When creating or editing alerts, you can describe your job requirements in natural language:
            
            "Looking for Senior Python Developer in Berlin, remote work possible, salary 80k+, no startups"
            
            The system will automatically parse:
            • Job Title: Senior Python Developer
            • Location: Berlin
            • Remote: Yes
            • Salary: 80k+
            • Filter: No startups
            
            **Alert Frequency:**
            You can specify how often to search:
            • Daily
            • Weekly
            • Monthly
            
            **Need More Help?**
            If you encounter any issues or need assistance, feel free to reach out or try /menu for quick access to all functions!
        """.trimIndent()

        try {
            sendMessage(chatId, helpMessage)
            // Reset to idle after showing help
            sessionManager.resetToIdle(userId)
        } catch (e: Exception) {
            logger.error(e) { "Error sending help message to user $userId" }
            sendMessage(chatId, "❌ Error displaying help. Please try again later.")
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