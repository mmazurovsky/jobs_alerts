package com.jobsalerts.core.bot

import com.jobsalerts.core.domain.model.*
import org.springframework.context.event.EventListener
import org.springframework.scheduling.annotation.Async
import org.springframework.stereotype.Service
import org.apache.logging.log4j.kotlin.Logging

@Service
class TelegramBotService : Logging {

    @EventListener
    @Async
    fun handleSendMessageEvent(event: SendMessageEvent) {
        logger.info { "Received message event from ${event.eventSource}: ${event.message}" }
        
        try {
            // TODO: Implement actual Telegram message sending
            // For now, just log the message
            if (event.chatId != null) {
                logger.info { "Would send message to chat ${event.chatId}: ${event.message}" }
            } else {
                logger.info { "Would send broadcast message: ${event.message}" }
            }
        } catch (e: Exception) {
            logger.error(e) { "Failed to send Telegram message" }
        }
    }

    // TODO: Event handlers will be re-added when JobEvent classes are uncommented
    
    // @EventListener
    // @Async
    // fun handleJobEvent(event: JobEvent) {
    //     // Implementation will be restored when JobEvent is uncommented
    // }
} 