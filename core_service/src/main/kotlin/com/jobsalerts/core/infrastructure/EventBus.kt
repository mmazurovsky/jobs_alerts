package com.jobsalerts.core.infrastructure

import kotlinx.coroutines.*
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.*
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.stereotype.Component
import kotlin.reflect.KClass

@Component
class EventBus : Logging {
    private val _events = Channel<Any>(Channel.UNLIMITED)
    
    @PublishedApi
    internal val events = _events.receiveAsFlow()
        .shareIn(
            scope = CoroutineScope(Dispatchers.Default + SupervisorJob()),
            started = SharingStarted.Eagerly,
            replay = 0
        )
    
    /**
     * Publish an event to all subscribers
     */
    fun publish(event: Any) {
        val result = _events.trySend(event)
        if (result.isFailure) {
            logger.warn { "Failed to publish event: ${event::class.simpleName}" }
        } else {
            logger.debug { "Published event: ${event::class.simpleName}" }
        }
    }
    
    /**
     * Subscribe to events of a specific type
     */
    final inline fun <reified T : Any> subscribe(): Flow<T> {
        return events.filterIsInstance<T>()
    }
    
    /**
     * Subscribe to events with a specific handler
     */
    final inline fun <reified T : Any> subscribe(
        scope: CoroutineScope,
        crossinline handler: suspend (T) -> Unit
    ): Job {
        return subscribe<T>()
            .onEach { event ->
                try {
                    handler(event)
                } catch (e: Exception) {
                    logger.error(e) { "Error handling event: ${event::class.simpleName}" }
                }
            }
            .launchIn(scope)
    }
} 