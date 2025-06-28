package com.jobsalerts.core.bot

import com.jobsalerts.core.domain.model.*
import com.jobsalerts.core.infrastructure.FromTelegramEventBus
import com.jobsalerts.core.infrastructure.ToTelegramEventBus
import com.jobsalerts.core.service.JobSearchService
import com.jobsalerts.core.service.ImmediateSearchService
import com.jobsalerts.core.service.AlertCreationService
import com.jobsalerts.core.service.SessionManager
import jakarta.annotation.PostConstruct
import jakarta.annotation.PreDestroy
import java.util.concurrent.ConcurrentHashMap
import kotlinx.coroutines.*
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.beans.factory.annotation.Value
import org.springframework.stereotype.Service
import org.telegram.telegrambots.bots.TelegramLongPollingBot
import org.telegram.telegrambots.meta.api.methods.send.SendMessage
import org.telegram.telegrambots.meta.api.objects.Update
import org.telegram.telegrambots.meta.api.objects.replykeyboard.ReplyKeyboardMarkup

import org.telegram.telegrambots.meta.exceptions.TelegramApiException

@Service
class TelegramBotService(
    @Value("\${telegram.bot.token}") private val botToken: String,
    @Value("\${telegram.bot.username}") private val botUsername: String,
    private val fromTelegramEventBus: FromTelegramEventBus,
    private val toTelegramEventBus: ToTelegramEventBus,
    private val jobSearchService: JobSearchService,
    private val immediateSearchService: ImmediateSearchService,
    private val alertCreationService: AlertCreationService,
    private val sessionManager: SessionManager
) : TelegramLongPollingBot(botToken), Logging, MessageSender {

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var outboundSubscription: Job? = null

    override fun getBotUsername(): String = botUsername

    @PostConstruct
    fun initialize() {
        outboundSubscription =
                toTelegramEventBus.subscribe(serviceScope) { event -> handleToTelegramEvent(event) }
        logger.info { "TelegramBotService initialized with bot username: $botUsername" }
    }

    @PreDestroy
    fun cleanup() {
        outboundSubscription?.cancel()
        serviceScope.cancel()
        logger.info { "TelegramBotService cleanup completed" }
    }

    override fun onUpdateReceived(update: Update) {
        serviceScope.launch {
            try {
                when {
                    update.hasMessage() -> {
                        val message = update.message
                        val chatId = message.chatId
                        val userId = message.from.id
                        val username = message.from.userName

                        logger.info { "Received message from user $userId: ${message.text?.take(50)}..." }

                        when {
                            message.hasText() && message.text.startsWith("/") -> {
                                val command =
                                        TelegramCommandParser.parseSlashCommand(
                                                chatId,
                                                userId,
                                                username,
                                                message.text
                                        )
                                command.execute(this@TelegramBotService, sessionManager, jobSearchService, immediateSearchService, alertCreationService)
                            }
                            message.hasText() -> {
                                val textMessage =
                                        TelegramCommandParser.parseTextMessage(
                                                chatId,
                                                userId,
                                                username,
                                                message.text,
                                                sessionManager.getCurrentContext(userId)
                                        )
                                textMessage.execute(this@TelegramBotService, sessionManager, jobSearchService, immediateSearchService, alertCreationService)
                            }
                        }
                    }
                    // Note: Callback queries removed - using slash commands only
                }
            } catch (e: Exception) {
                logger.error(e) { "Error processing update: ${update}" }
            }
        }
    }



    // Implementation of MessageSender interface
    override suspend fun sendMessage(chatId: Long, message: String) {
        sendMessageWithSplitting(chatId, message)
    }

    // Event handling for outbound messages
    private suspend fun handleToTelegramEvent(event: ToTelegramEvent) {
        try {
            when (event) {
                is ToTelegramSendMessageEvent -> {
                    sendMessageWithSplitting(event.chatId, event.message)
                }
                is SearchResultsToTelegramEvent -> {
                    val message = buildString {
                        appendLine("🔔 New job listings found for your search.\n")
                        event.eventData.forEach { job ->
                            appendLine(job.toMessage())
                            appendLine()
                        }
                    }
                    sendMessageWithSplitting(event.chatId, message)
                }
            }
        } catch (e: Exception) {
            logger.error(e) { "Error handling ToTelegramEvent: $event" }
        }
    }

    private suspend fun sendMessageWithSplitting(
            chatId: Long,
            message: String,
    ) {
        val maxLength = 4096 // Telegram message length limit

        val adjustedMaxLength = maxLength

        val messageParts = splitMessage(message, adjustedMaxLength)
        messageParts.forEachIndexed { index, part ->
            val messageToSend =
                    if (index == 0) {
                        part
                    } else {
                        "(continued...)\n$part"
                    }

            sendSingleMessage(chatId, messageToSend)

            // Small delay between messages to avoid rate limiting
            if (index < messageParts.size - 1) {
                delay(100)
            }
        }
    }

    private fun splitMessage(message: String, maxLength: Int): List<String> {
        if (message.length <= maxLength) return listOf(message)

        val parts = mutableListOf<String>()
        val paragraphs = message.split("\n\n")
        var currentPart = ""

        for (paragraph in paragraphs) {
            if ((currentPart + paragraph).length <= maxLength) {
                currentPart += if (currentPart.isEmpty()) paragraph else "\n\n$paragraph"
            } else {
                if (currentPart.isNotEmpty()) {
                    parts.add(currentPart)
                }
                currentPart =
                        if (paragraph.length > maxLength) {
                            parts.addAll(splitLongText(paragraph, maxLength))
                            ""
                        } else {
                            paragraph
                        }
            }
        }

        if (currentPart.isNotEmpty()) {
            parts.add(currentPart)
        }

        return parts
    }

    private fun splitLongText(text: String, maxLength: Int): List<String> {
        return text.chunked(maxLength)
    }

    private suspend fun sendSingleMessage(
            chatId: Long,
            message: String
    ) {
        try {
            val sendMessage =
                    SendMessage.builder()
                            .chatId(chatId.toString())
                            .text(message)
                            .build()

            execute(sendMessage)

            logger.debug { "Message sent to chat $chatId" }
        } catch (e: TelegramApiException) {
            logger.error(e) { "Failed to send message to chat $chatId: ${e.message}" }
        }
    }
}
