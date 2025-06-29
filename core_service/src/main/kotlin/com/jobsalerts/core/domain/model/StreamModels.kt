package com.jobsalerts.core.domain.model

import org.springframework.context.ApplicationEvent

// Base event for all job alerts events
sealed class ToTelegramEvent(
    open val eventData: Any,
    open val eventSource: String,
    val timestamp: Long = System.currentTimeMillis()
)

data class SearchResultsToTelegramEvent(
    val chatId: Long,
    override val eventData: List<FullJobListing>,
    override val eventSource: String,
) : ToTelegramEvent(eventData, eventSource)

// Message events for Telegram bot communication
data class ToTelegramSendMessageEvent(
    val message: String,
    val chatId: Long,
    override val eventSource: String
) : ToTelegramEvent(message, eventSource)

// Events coming FROM Telegram
sealed class FromTelegramEvent(
        open val message: String,
        open val userId: Long,
        val timestamp: Long = System.currentTimeMillis()
)

data class TelegramMessageReceived(
        override val message: String,
        val text: String,
        val userName: String?,
        override val userId: Long,
        val chatId: Long,
        val commandName: String? = null,
        val commandParameters: String? = null,
) : FromTelegramEvent(message, userId)
