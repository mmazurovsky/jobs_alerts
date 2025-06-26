package com.jobsalerts.core.infrastructure

import com.jobsalerts.core.domain.model.SendMessageEvent
import kotlinx.coroutines.*
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.*
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.stereotype.Component

@Component
class ToTelegramEventBus : Logging {
    private val _messageEvents = Channel<SendMessageEvent>(Channel.UNLIMITED)
    
    @PublishedApi
    internal val messageEvents = _messageEvents.receiveAsFlow()
        .shareIn(
            scope = CoroutineScope(Dispatchers.Default + SupervisorJob()),
            started = SharingStarted.Eagerly,
            replay = 0
        )
    
    /**
     * Send a message to Telegram
     */
    fun sendMessage(message: String, chatId: Long? = null, source: String = "system") {
        val event = SendMessageEvent(message, chatId, source)
        val result = _messageEvents.trySend(event)
        
        if (result.isFailure) {
            logger.warn { "Failed to queue Telegram message: $message" }
        } else {
            logger.debug { "Queued Telegram message from $source: $message" }
        }
    }
    
    /**
     * Send a broadcast message to all subscribers
     */
    fun broadcast(message: String, source: String = "system") {
        sendMessage(message, null, source)
    }
    
    /**
     * Subscribe to outbound message events
     */
    fun subscribeToMessages(): Flow<SendMessageEvent> {
        return messageEvents
    }
    
    /**
     * Subscribe to outbound messages with a handler
     */
    fun subscribeToMessages(
        scope: CoroutineScope,
        handler: suspend (SendMessageEvent) -> Unit
    ): Job {
        return messageEvents
            .onEach { event ->
                try {
                    handler(event)
                } catch (e: Exception) {
                    logger.error(e) { "Error handling outbound Telegram message: ${event.message}" }
                }
            }
            .launchIn(scope)
    }
} 