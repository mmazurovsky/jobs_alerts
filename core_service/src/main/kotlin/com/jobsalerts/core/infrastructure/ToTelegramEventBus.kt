package com.jobsalerts.core.infrastructure

import com.jobsalerts.core.domain.model.ToTelegramSendMessageEvent
import com.jobsalerts.core.domain.model.ToTelegramEvent
import kotlinx.coroutines.*
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.*
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.stereotype.Component

@Component
class ToTelegramEventBus : Logging {
    private val _events = Channel<ToTelegramSendMessageEvent>(Channel.UNLIMITED)
    private val subscribers = mutableSetOf<Job>()
    
    @PublishedApi
    internal val events = _events.receiveAsFlow()
        .shareIn(
            scope = CoroutineScope(Dispatchers.Default + SupervisorJob()),
            started = SharingStarted.Eagerly,
            replay = 0
        )
    
    /**
     * Subscribe to outbound message events
     */
    fun subscribe(
        scope: CoroutineScope,
        handler: suspend (ToTelegramEvent) -> Unit
    ): Job {
        val job = events
            .onEach { event ->
                try {
                    handler(event)
                } catch (e: Exception) {
                    logger.error(e) { "Error handling outbound Telegram message: ${event.message}" }
                }
            }
            .launchIn(scope)
        
        subscribers.add(job)
        logger.debug { "Subscribed to ToTelegramEvent events" }
        return job
    }
    
    /**
     * Unsubscribe from events
     */
    fun unsubscribe(job: Job) {
        job.cancel()
        subscribers.remove(job)
        logger.debug { "Unsubscribed from outbound Telegram messages" }
    }
    
    /**
     * Publish a message event (for internal use by services)
     */
    internal fun publish(event: ToTelegramSendMessageEvent) {
        val result = _events.trySend(event)
        
        if (result.isFailure) {
            logger.warn { "Failed to queue Telegram message: ${event.message}" }
        } else {
            logger.debug { "Queued Telegram message from ${event.eventSource}: ${event.message}" }
        }
    }
} 