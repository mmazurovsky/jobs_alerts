package com.jobsalerts.core.infrastructure

import kotlinx.coroutines.*
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.*
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.stereotype.Component

// Events coming FROM Telegram
sealed class TelegramInboundEvent(
    val userId: Long,
    val chatId: Long,
    val timestamp: Long = System.currentTimeMillis()
)

data class TelegramMessageReceived(
    val messageId: Int,
    val text: String,
    val userName: String?,
    private val userIdValue: Long,
    private val chatIdValue: Long
) : TelegramInboundEvent(userIdValue, chatIdValue)

data class TelegramCallbackReceived(
    val callbackId: String,
    val data: String,
    val messageId: Int?,
    private val userIdValue: Long,
    private val chatIdValue: Long
) : TelegramInboundEvent(userIdValue, chatIdValue)

data class TelegramCommandReceived(
    val command: String,
    val parameters: List<String>,
    val messageId: Int,
    private val userIdValue: Long,
    private val chatIdValue: Long
) : TelegramInboundEvent(userIdValue, chatIdValue)

@Component
class FromTelegramEventBus : Logging {
    private val _inboundEvents = Channel<TelegramInboundEvent>(Channel.UNLIMITED)
    
    @PublishedApi
    internal val inboundEvents = _inboundEvents.receiveAsFlow()
        .shareIn(
            scope = CoroutineScope(Dispatchers.Default + SupervisorJob()),
            started = SharingStarted.Eagerly,
            replay = 0
        )
    
    /**
     * Publish a message received from Telegram
     */
    fun onMessageReceived(
        messageId: Int,
        text: String,
        userId: Long,
        chatId: Long,
        userName: String? = null
    ) {
        val event = TelegramMessageReceived(messageId, text, userName, userId, chatId)
        publishEvent(event)
    }
    
    /**
     * Publish a callback received from Telegram
     */
    fun onCallbackReceived(
        callbackId: String,
        data: String,
        userId: Long,
        chatId: Long,
        messageId: Int? = null
    ) {
        val event = TelegramCallbackReceived(callbackId, data, messageId, userId, chatId)
        publishEvent(event)
    }
    
    /**
     * Publish a command received from Telegram
     */
    fun onCommandReceived(
        command: String,
        parameters: List<String>,
        messageId: Int,
        userId: Long,
        chatId: Long
    ) {
        val event = TelegramCommandReceived(command, parameters, messageId, userId, chatId)
        publishEvent(event)
    }
    
    private fun publishEvent(event: TelegramInboundEvent) {
        val result = _inboundEvents.trySend(event)
        if (result.isFailure) {
            logger.warn { "Failed to publish inbound Telegram event: ${event::class.simpleName}" }
        } else {
            logger.debug { "Published inbound Telegram event: ${event::class.simpleName} from user ${event.userId}" }
        }
    }
    
    /**
     * Subscribe to all inbound events
     */
    final inline fun <reified T : TelegramInboundEvent> subscribe(): Flow<T> {
        return inboundEvents.filterIsInstance<T>()
    }
    
    /**
     * Subscribe to inbound events with a handler
     */
    final inline fun <reified T : TelegramInboundEvent> subscribe(
        scope: CoroutineScope,
        crossinline handler: suspend (T) -> Unit
    ): Job {
        return subscribe<T>()
            .onEach { event ->
                try {
                    handler(event)
                } catch (e: Exception) {
                    logger.error(e) { "Error handling inbound Telegram event: ${event::class.simpleName}" }
                }
            }
            .launchIn(scope)
    }
    
    /**
     * Subscribe to messages (text messages from users)
     */
    fun subscribeToMessages(): Flow<TelegramMessageReceived> = subscribe()
    
    /**
     * Subscribe to callbacks (button clicks, inline keyboards)
     */
    fun subscribeToCallbacks(): Flow<TelegramCallbackReceived> = subscribe()
    
    /**
     * Subscribe to commands (e.g., /start, /help)
     */
    fun subscribeToCommands(): Flow<TelegramCommandReceived> = subscribe()
} 