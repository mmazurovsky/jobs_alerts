package com.jobsalerts.core.bot

import com.jobsalerts.core.Messages
import com.jobsalerts.core.domain.model.*
import com.jobsalerts.core.infrastructure.FromTelegramEventBus
import com.jobsalerts.core.infrastructure.ToTelegramEventBus
import com.jobsalerts.core.service.*
import dev.inmo.tgbotapi.bot.ktor.telegramBot
import dev.inmo.tgbotapi.extensions.api.bot.getMe
import dev.inmo.tgbotapi.extensions.api.send.sendTextMessage
import dev.inmo.tgbotapi.extensions.behaviour_builder.buildBehaviourWithLongPolling
import dev.inmo.tgbotapi.extensions.behaviour_builder.triggers_handling.onText
import dev.inmo.tgbotapi.extensions.behaviour_builder.triggers_handling.onCommand
import dev.inmo.tgbotapi.types.message.abstracts.CommonMessage
import dev.inmo.tgbotapi.types.message.content.TextContent
import dev.inmo.tgbotapi.types.message.abstracts.FromUserMessage
import dev.inmo.tgbotapi.types.ChatId
import dev.inmo.tgbotapi.types.toChatId
import jakarta.annotation.PostConstruct
import jakarta.annotation.PreDestroy
import kotlinx.coroutines.*
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.beans.factory.annotation.Value
import org.springframework.stereotype.Service

@Service
class TelegramBotService(
    @Value("\${TELEGRAM_BOT_TOKEN}") private val botToken: String,
    private val fromTelegramEventBus: FromTelegramEventBus,
    private val toTelegramEventBus: ToTelegramEventBus
) : Logging {

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var outboundSubscription: Job? = null
    private var botJob: Job? = null
    private val bot = telegramBot(botToken)
    private var botName: String = ""

    @PostConstruct
    fun initialize() {
        logger.info { "🔧 TelegramBotService: Starting initialization..." }
        
        // Subscribe to outbound events
        outboundSubscription = toTelegramEventBus.subscribe(serviceScope) { event -> 
            handleToTelegramEvent(event) 
        }
        logger.info { "📬 TelegramBotService: Subscribed to outbound events" }
        
        // Check bot info first
        runBlocking {
            checkBotInfo()
        }
        
        // Start the bot in background
        serviceScope.launch {
            initBot()
        }
        
        logger.info { "✅ TelegramBotService: Initialization completed" }
    }

    @PreDestroy
    fun cleanup() {
        outboundSubscription?.cancel()
        botJob?.cancel()
        serviceScope.cancel()
        logger.info { "TelegramBotService cleanup completed" }
    }

    private suspend fun checkBotInfo() {
        try {
            logger.info { "🤖 TelegramBotService: Testing bot connection..." }
            val me = bot.getMe()
            botName = me.firstName ?: me.username?.username ?: "Unknown"
            logger.info { "🤖 TelegramBotService initialized with bot username: ${me.username}" }
            logger.info { "🔧 TelegramBotService: Bot token starts with: ${botToken.take(10)}..." }
        } catch (e: Exception) {
            logger.error(e) { "💥 TelegramBotService: Error checking bot info" }
            throw e
        }
    }

    private suspend fun initBot() {
        try {
            logger.info { "📡 TelegramBotService: Starting long polling bot..." }
            
            bot.buildBehaviourWithLongPolling {
                logger.info { "🚀 TelegramBotService: Long polling started successfully" }
                
                // Handle all text messages - this will process both commands with parameters and regular text
                onText { message ->
                    val messageText = message.content.text
                    if (messageText.startsWith("/")) {
                        // Handle commands that have parameters
                        val parts = messageText.split(" ", limit = 2)
                        val commandName = parts[0].lowercase()
                        val hasParameters = parts.size > 1 && parts[1].trim().isNotEmpty()
                        
                        if (hasParameters && commandName in listOf("/delete_alert", "/edit_alert", "/search_now")) {
                            logger.info { "⚡ TelegramBotService: Received command with parameters: $messageText" }
                            handleIncomingMessage(message)
                        } else if (!hasParameters && commandName !in listOf("/start", "/help", "/menu", "/create_alert", "/list_alerts", "/delete_alert", "/edit_alert", "/search_now", "/cancel")) {
                            // Handle any unknown commands
                            logger.info { "⚡ TelegramBotService: Received unknown command: $messageText" }
                            handleIncomingMessage(message)
                        }
                        // Commands without parameters are handled by onCommand handlers
                    } else {
                        // Handle regular text messages (non-commands)
                        logger.info { "📩 TelegramBotService: Received non-command text message" }
                        handleIncomingMessage(message)
                    }
                }
                
                // Handle simple commands without parameters
                onCommand("start") { message ->
                    logger.info { "⚡ TelegramBotService: Received /start command" }
                    handleIncomingMessage(message)
                }
                
                onCommand("help") { message ->
                    logger.info { "⚡ TelegramBotService: Received /help command" }
                    handleIncomingMessage(message)
                }
                
                onCommand("menu") { message ->
                    logger.info { "⚡ TelegramBotService: Received /menu command" }
                    handleIncomingMessage(message)
                }
                
                onCommand("create_alert") { message ->
                    logger.info { "⚡ TelegramBotService: Received /create_alert command" }
                    handleIncomingMessage(message)
                }
                
                onCommand("list_alerts") { message ->
                    logger.info { "⚡ TelegramBotService: Received /list_alerts command" }
                    handleIncomingMessage(message)
                }
                
                onCommand("delete_alert") { message ->
                    logger.info { "⚡ TelegramBotService: Received /delete_alert command (no parameters)" }
                    handleIncomingMessage(message)
                }
                
                onCommand("edit_alert") { message ->
                    logger.info { "⚡ TelegramBotService: Received /edit_alert command (no parameters)" }
                    handleIncomingMessage(message)
                }
                
                onCommand("search_now") { message ->
                    logger.info { "⚡ TelegramBotService: Received /search_now command (no parameters)" }
                    handleIncomingMessage(message)
                }
                
                onCommand("cancel") { message ->
                    logger.info { "⚡ TelegramBotService: Received /cancel command" }
                    handleIncomingMessage(message)
                }
            }
            
            logger.info { "✅ TelegramBotService: Bot initialization completed" }
            
        } catch (e: Exception) {
            logger.error(e) { "💥 TelegramBotService: Error starting bot" }
            // Try to restart after delay
            delay(5000)
            logger.info { "🔄 TelegramBotService: Attempting to restart bot..." }
            initBot()
        }
    }

    private suspend fun handleIncomingMessage(message: CommonMessage<TextContent>) {
        try {
            val chatId = message.chat.id.chatId.long
            val userId = (message as? dev.inmo.tgbotapi.types.message.abstracts.FromUserMessage)?.from?.id?.chatId?.long ?: return
            val username = (message as? dev.inmo.tgbotapi.types.message.abstracts.FromUserMessage)?.from?.username?.username
            val messageText = message.content.text
            
            logger.info { "📥 TELEGRAM MESSAGE RECEIVED from user $userId (username: $username, chatId: $chatId)" }
            logger.info { "📱 MESSAGE TEXT: '$messageText'" }

            val isCommand = messageText.startsWith("/")
            logger.info { "📝 MESSAGE ANALYSIS: isCommand=$isCommand" }

            // Extract command information if it's a command
            val (commandName, commandParameters) = if (isCommand) {
                val parts = messageText.split(" ", limit = 2)
                val command = parts[0].lowercase()
                val parameters = if (parts.size > 1) parts[1] else null
                logger.info { "🔧 COMMAND PARSED: name='$command', parameters='$parameters'" }
                Pair(command, parameters)
            } else {
                Pair(null, null)
            }

            val telegramEvent = TelegramMessageReceived(
                message = messageText,
                text = messageText,
                username = username,
                userId = userId,
                chatId = chatId,
                commandName = commandName,
                commandParameters = commandParameters,
            )

            logger.info { "🚀 PUBLISHING EVENT to event bus: $telegramEvent" }
            fromTelegramEventBus.publish(telegramEvent)
            logger.info { "✅ EVENT PUBLISHED successfully" }
            
        } catch (e: Exception) {
            logger.error(e) { "💥 ERROR PROCESSING MESSAGE: ${message}" }
        }
    }

    // Event handling for outbound messages
    private suspend fun handleToTelegramEvent(event: ToTelegramEvent) {
        logger.info { "📬 TelegramBotService: HANDLING OUTBOUND EVENT: $event" }
        try {
            when (event) {
                is ToTelegramSendMessageEvent -> {
                    logger.info { "💬 TelegramBotService: Sending message to chatId=${event.chatId} from ${event.eventSource}" }
                    sendMessageWithSplitting(event.chatId.toChatId(), event.message)
                }
                is SearchResultsToTelegramEvent -> {
                    logger.info { "🔍 TelegramBotService: Sending search results to chatId=${event.chatId}, jobCount=${event.eventData.size}" }
                    sendMessageWithSplitting(event.chatId.toChatId(), Messages.getJobResultsMessage(event.eventData))
                }
            }
            logger.info { "✅ TelegramBotService: Successfully handled outbound event" }
        } catch (e: Exception) {
            logger.error(e) { "💥 TelegramBotService: Error handling ToTelegramEvent: $event" }
        }
    }

    private suspend fun sendMessageWithSplitting(chatId: ChatId, message: String) {
        val maxLength = 4096 // Telegram message length limit
        val messageParts = splitMessage(message, maxLength)
        
        messageParts.forEachIndexed { index, part ->
            val messageToSend = if (index == 0) {
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
                currentPart = if (paragraph.length > maxLength) {
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

    private suspend fun sendSingleMessage(chatId: ChatId, message: String) {
        try {
            logger.info { "📡 TelegramBotService: Executing Telegram API call for chatId=$chatId, messageLength=${message.length}" }
            
            bot.sendTextMessage(chatId, message)
            
            logger.info { "✅ TelegramBotService: Message sent successfully to chat $chatId" }
        } catch (e: Exception) {
            logger.error(e) { "💥 TelegramBotService: Failed to send message to chat $chatId: ${e.message}" }
        }
    }
}

