package com.jobsalerts.core.infrastructure

import kotlinx.coroutines.*
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.*
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.stereotype.Component
import com.jobsalerts.core.domain.model.FromTelegramEvent

@Component
class FromTelegramEventBus : Logging {
    private val _events = Channel<FromTelegramEvent>(Channel.UNLIMITED)
    private val subscribers = mutableSetOf<Job>()

    @PublishedApi
    internal val events =
            _events.receiveAsFlow()
                    .shareIn(
                            scope = CoroutineScope(Dispatchers.Default + SupervisorJob()),
                            started = SharingStarted.Eagerly,
                            replay = 0
                    )

    /** Subscribe to events of a specific type **/
    fun subscribe(scope: CoroutineScope, handler: suspend (FromTelegramEvent) -> Unit): Job {
        val job = events
            .onEach { event ->
                try {
                    handler(event)
                } catch (e: Exception) {
                    logger.error(e) { "Error handling from Telegram message: ${event.message}" }
                }
            }
            .launchIn(scope)

        subscribers.add(job)
        logger.debug { "Subscribed to FromTelegramEvent events" }
        return job
    }

    /** Unsubscribe from events */
    fun unsubscribe(job: Job) {
        job.cancel()
        subscribers.remove(job)
        logger.debug { "Unsubscribed from events" }
    }

    /** Publish an event (for internal use by bot service) */
    internal fun publish(event: FromTelegramEvent) {
        val result = _events.trySend(event)
        if (result.isFailure) {
            logger.warn { "Failed to publish Telegram event: ${event::class.simpleName}" }
        } else {
            logger.debug {
                "Published Telegram event: ${event::class.simpleName} from user ${event.userId}"
            }
        }
    }
}
