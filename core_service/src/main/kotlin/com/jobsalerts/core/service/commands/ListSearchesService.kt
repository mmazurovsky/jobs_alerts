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
class ListSearchesService(
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
                    sessionManager.setContext(event.userId, ListAlertsSubContext.ViewingList)
                    try {
                        processListRequest(event.chatId, event.userId)
                    } catch (e: Exception) {
                        logger.error(e) { "Error processing list request for user ${event.userId}" }
                        sendMessage(event.chatId, "❌ Error retrieving your job alerts. Please try again later.")
                        sessionManager.resetToIdle(event.userId)
                    }
                }
                
                event.commandName == "/cancel" && currentContext is ListAlertsSubContext -> {
                    sendMessage(event.chatId, "❌ List operation cancelled.")
                    sessionManager.resetToIdle(event.userId)
                }
            }
        }
    }

    private suspend fun processListRequest(chatId: Long, userId: Long) {
        try {
            val userSearches = jobSearchService.getUserSearches(userId)
            
            if (userSearches.isEmpty()) {
                val message = """
                    📋 **Your Job Alerts**
                    
                    You don't have any active job alerts yet.
                    
                    **Get started:**
                    /create_alert - Create your first job alert
                    /help - See all available commands
                    
                    Ready to find your next opportunity? 🚀
                """.trimIndent()
                
                sendMessage(chatId, message)
            } else {
                val message = buildString {
                    appendLine("📋 **Your Active Job Alerts** (${userSearches.size} total)\n")
                    
                    userSearches.forEach { jobSearch ->
                        append(jobSearch.toMessage())
                        appendLine("─".repeat(40))
                        appendLine()
                    }
                    
                    appendLine("**Available Actions:**")
                    appendLine("/edit_alert [ID] - Edit a specific alert")
                    appendLine("/delete_alert [ID] - Delete a specific alert")
                    appendLine("/create_alert - Create a new alert")
                    appendLine("/search_now - Run an immediate search")
                }
                
                sendMessage(chatId, message.toString())
            }
            
            // Reset to idle after showing the list
            sessionManager.resetToIdle(userId)
            
        } catch (e: Exception) {
            logger.error(e) { "Error retrieving job alerts for user $userId" }
            sendMessage(chatId, "❌ Error retrieving your job alerts. Please try again later.")
            sessionManager.resetToIdle(userId)
        }
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