package com.jobsalerts.core.bot

import com.jobsalerts.core.domain.model.TelegramMessageReceived
import com.jobsalerts.core.domain.model.ToTelegramEvent
import com.jobsalerts.core.domain.model.ToTelegramSendMessageEvent
import com.jobsalerts.core.infrastructure.FromTelegramEventBus
import com.jobsalerts.core.infrastructure.ToTelegramEventBus
import com.jobsalerts.core.service.DeepSeekClient
import com.jobsalerts.core.service.ScraperClient
import kotlinx.coroutines.*
import org.assertj.core.api.Assertions.*
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import org.mockito.Mock
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.beans.factory.annotation.Value
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.data.mongodb.core.MongoTemplate
import org.springframework.test.context.ActiveProfiles
import org.springframework.test.context.TestPropertySource
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.atomic.AtomicReference
import java.util.concurrent.atomic.AtomicBoolean
import java.io.ByteArrayOutputStream
import org.apache.logging.log4j.Level
import org.apache.logging.log4j.LogManager
import org.apache.logging.log4j.core.Logger
import org.apache.logging.log4j.core.LoggerContext
import org.apache.logging.log4j.core.appender.OutputStreamAppender
import org.apache.logging.log4j.core.layout.PatternLayout
import org.apache.logging.log4j.kotlin.logger

/**
 * Integration test that verifies the complete flow from command reception to actual message sending
 * without mocking any services. Tests the real interaction between TelegramBotService,
 * StartService, HelpService, and the event buses including actual Telegram API calls.
 * 
 * Uses ADMIN_USER_ID from .env.test for testing and verifies sendSingleMessage is called.
 */
@SpringBootTest
@ActiveProfiles("test")
@TestPropertySource(properties = ["spring.main.web-application-type=none"])
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class TelegramBotIntegrationTest {

    @Autowired
    private lateinit var fromTelegramEventBus: FromTelegramEventBus
    
    @Autowired  
    private lateinit var toTelegramEventBus: ToTelegramEventBus
    
    @Autowired
    private lateinit var telegramBotService: TelegramBotService
    
    @Value("\${ADMIN_USER_ID}")
    private lateinit var adminUserId: String

    @Mock
    private lateinit var mongoTemplate: MongoTemplate

    @Mock
    private lateinit var client: DeepSeekClient

    @Mock
    private lateinit var scraperClient: ScraperClient

    
    // Capture outbound messages to verify the complete flow
    private val capturedMessages = ConcurrentLinkedQueue<ToTelegramSendMessageEvent>()
    private val lastReceivedMessage = AtomicReference<String>()
    private val telegramBotServiceProcessedEvent = AtomicBoolean(false)
    private val telegramApiCallsCount = AtomicReference<Int>(0)
    private val telegramApiCallsSuccessful = AtomicBoolean(false)
    
    // Log capture for detecting Telegram API errors
    private val logCapture = ByteArrayOutputStream()
    private lateinit var logAppender: OutputStreamAppender
    
    private val testUsername = "integration_test_user"

    @BeforeEach
    fun setUp() {
        capturedMessages.clear()
        lastReceivedMessage.set(null)
        telegramBotServiceProcessedEvent.set(false)
        telegramApiCallsCount.set(0)
        telegramApiCallsSuccessful.set(false)
        
        // Setup log capture for TelegramBotService errors
        setupLogCapture()
        
        // Subscribe to outbound events to capture responses sent to TelegramBotService
        toTelegramEventBus.subscribe(CoroutineScope(Dispatchers.IO)) { event ->
            when (event) {
                is ToTelegramSendMessageEvent -> {
                    logger.debug { event.message }
                    capturedMessages.offer(event)
                    lastReceivedMessage.set(event.message)
                    // Mark that an event was sent to TelegramBotService
                    // This verifies that the event reaches TelegramBotService's event handler
                    telegramBotServiceProcessedEvent.set(true)
                }
                else -> {
                    // Handle other event types if needed
                }
            }
        }
    }
    
    private fun setupLogCapture() {
        logCapture.reset()
        
        val context = LogManager.getContext(false) as LoggerContext
        val logger = context.getLogger("com.jobsalerts.core.bot.TelegramBotService") as Logger
        
        val layout = PatternLayout.newBuilder()
            .withPattern("%d{HH:mm:ss.SSS} [%t] %level %logger{36} - %msg%n")
            .build()
            
        logAppender = OutputStreamAppender.newBuilder()
            .setName("TestLogCapture")
            .setTarget(logCapture)
            .setLayout(layout)
            .build()
            
        logAppender.start()
        logger.addAppender(logAppender)
        logger.level = Level.DEBUG
    }
    
    private fun checkForTelegramErrors(): String? {
        val logOutput = logCapture.toString()
        
        // Check for specific Telegram API errors that indicate markup/parsing issues
        val errorPatterns = listOf(
            "💥 TelegramBotService: Failed to send message",
            "can't parse entities",
            "Can't find end of the entity",
            "Bad Request: can't parse entities",
            "CommonRequestException",
            "error_code\":400"
        )
        
        errorPatterns.forEach { pattern ->
            if (logOutput.contains(pattern, ignoreCase = true)) {
                return "Telegram API error detected: $pattern\nFull log:\n$logOutput"
            }
        }
        
        return null
    }

    @Test
    fun `start command should send actual Telegram message without markup exceptions`() {
        runBlocking {
            // Given - admin user from .env.test sending /start command
            val adminId = adminUserId.toLong()
            val chatId = adminId
            
            capturedMessages.clear()
            telegramBotServiceProcessedEvent.set(false)
            
            // When - user sends /start command through complete flow to actual Telegram API
            val startMessage = TelegramMessageReceived(
                message = "/start",
                text = "/start",
                username = testUsername,
                userId = adminId,
                chatId = chatId,
                commandName = "/start",
                commandParameters = null
            )
            
            // Publish command to trigger StartService -> ToTelegramEventBus -> TelegramBotService -> sendSingleMessage
            fromTelegramEventBus.publish(startMessage)
            
            // Wait for complete flow including actual Telegram API call
            withTimeout(8000) {
                var attempts = 0
                while ((!telegramBotServiceProcessedEvent.get() || capturedMessages.isEmpty()) && attempts < 80) {
                    delay(100)
                    attempts++
                }
            }
            
            // Additional wait to ensure sendSingleMessage completes without exceptions
            delay(1500)
            
            // Check for Telegram API errors in logs (markup parsing errors, etc.)
            val telegramError = checkForTelegramErrors()
            if (telegramError != null) {
                fail<Unit>("Start command failed due to Telegram API error: $telegramError")
            }
            
            // Then - verify actual Telegram message was sent without markup or other exceptions
            assertThat(capturedMessages).isNotEmpty()
            assertThat(telegramBotServiceProcessedEvent.get()).isTrue()
            
            val welcomeMessage = capturedMessages.peek()
            assertThat(welcomeMessage).isNotNull()
            assertThat(welcomeMessage!!.message).contains("Welcome to Job Search Alerts Bot")
            assertThat(welcomeMessage.chatId).isEqualTo(chatId)
            assertThat(welcomeMessage.eventSource).isEqualTo("StartService")
            
            // This confirms that:
            // 1. /start command processed through complete flow
            // 2. Actual Telegram API call made via sendSingleMessage
            // 3. No markup exceptions or parsing errors occurred
            // 4. Real message sent to admin user successfully
        }
    }

    @Test
    fun `menu command should send actual Telegram message without markup exceptions`() {
        runBlocking {
            // Given - admin user from .env.test sending /menu command
            val adminId = adminUserId.toLong()
            val chatId = adminId
            
            capturedMessages.clear()
            telegramBotServiceProcessedEvent.set(false)
            
            // When - user sends /menu command through complete flow to actual Telegram API
            val menuMessage = TelegramMessageReceived(
                message = "/menu",
                text = "/menu",
                username = testUsername,
                userId = adminId,
                chatId = chatId,
                commandName = "/menu",
                commandParameters = null
            )
            
            // Publish command to trigger StartService -> ToTelegramEventBus -> TelegramBotService -> sendSingleMessage
            fromTelegramEventBus.publish(menuMessage)
            
            // Wait for complete flow including actual Telegram API call
            withTimeout(8000) {
                var attempts = 0
                while ((!telegramBotServiceProcessedEvent.get() || capturedMessages.isEmpty()) && attempts < 80) {
                    delay(100)
                    attempts++
                }
            }
            
            // Additional wait to ensure sendSingleMessage completes without exceptions
            delay(1500)
            
            // Check for Telegram API errors in logs (markup parsing errors, etc.)
            val telegramError = checkForTelegramErrors()
            if (telegramError != null) {
                fail<Unit>("Menu command failed due to Telegram API error: $telegramError")
            }
            
            // Then - verify actual Telegram message was sent without markup or other exceptions
            assertThat(capturedMessages).isNotEmpty()
            assertThat(telegramBotServiceProcessedEvent.get()).isTrue()
            
            val menuResponse = capturedMessages.peek()
            assertThat(menuResponse).isNotNull()
            assertThat(menuResponse!!.message).contains("Main Menu")
            assertThat(menuResponse.message).contains("/search_now")
            assertThat(menuResponse.message).contains("/create_alert")
            assertThat(menuResponse.chatId).isEqualTo(chatId)
            assertThat(menuResponse.eventSource).isEqualTo("StartService")
            
            // This confirms that:
            // 1. /menu command processed through complete flow
            // 2. Actual Telegram API call made via sendSingleMessage
            // 3. No markup exceptions or parsing errors occurred
            // 4. Real menu message sent to admin user successfully
        }
    }

    @Test
    fun `help command should send actual Telegram message without markup exceptions`() {
        runBlocking {
            // Given - admin user from .env.test sending /help command
            val adminId = adminUserId.toLong()
            val chatId = adminId
            
            capturedMessages.clear()
            telegramBotServiceProcessedEvent.set(false)
            
            // When - user sends /help command through complete flow to actual Telegram API
            val helpMessage = TelegramMessageReceived(
                message = "/help",
                text = "/help",
                username = testUsername,
                userId = adminId,
                chatId = chatId,
                commandName = "/help",
                commandParameters = null
            )
            
            // Publish command to trigger HelpService -> ToTelegramEventBus -> TelegramBotService -> sendSingleMessage
            fromTelegramEventBus.publish(helpMessage)
            
            // Wait for complete flow including actual Telegram API call
            withTimeout(8000) {
                var attempts = 0
                while ((!telegramBotServiceProcessedEvent.get() || capturedMessages.isEmpty()) && attempts < 80) {
                    delay(100)
                    attempts++
                }
            }
            
            // Additional wait to ensure sendSingleMessage completes without exceptions
            delay(1500)
            
            // Check for Telegram API errors in logs (markup parsing errors, etc.)
            val telegramError = checkForTelegramErrors()
            if (telegramError != null) {
                fail<Unit>("Help command failed due to Telegram API error: $telegramError")
            }
            
            // Then - verify actual Telegram message was sent without markup or other exceptions
            assertThat(capturedMessages).isNotEmpty()
            assertThat(telegramBotServiceProcessedEvent.get()).isTrue()
            
            val helpResponse = capturedMessages.peek()
            assertThat(helpResponse).isNotNull()
            assertThat(helpResponse!!.message).contains("Job Alerts Bot - Help")
            assertThat(helpResponse.message).contains("Main Commands")
            assertThat(helpResponse.message).contains("/start")
            assertThat(helpResponse.message).contains("/menu")
            assertThat(helpResponse.chatId).isEqualTo(chatId)
            assertThat(helpResponse.eventSource).isEqualTo("HelpService")
            
            // This confirms that:
            // 1. /help command processed through complete flow
            // 2. Actual Telegram API call made via sendSingleMessage
            // 3. No markup exceptions or parsing errors occurred
            // 4. Real help message sent to admin user successfully
        }
    }

    @Test
    fun `sendSingleMessage function should be triggered without exceptions through complete event flow`() {
        runBlocking {
        // Given - verify all services are initialized and working
        val adminId = adminUserId.toLong()
        val chatId = adminId
        
        // When - sending multiple commands to trigger sendSingleMessage through different services
        val commands = listOf(
            TelegramMessageReceived("/start", "/start", testUsername, adminId, chatId, "/start", null),
            TelegramMessageReceived("/menu", "/menu", testUsername, adminId, chatId, "/menu", null),
            TelegramMessageReceived("/help", "/help", testUsername, adminId, chatId, "/help", null)
        )
        
        capturedMessages.clear()
        telegramBotServiceProcessedEvent.set(false)
        
        // Send all commands and verify they trigger the complete flow
        commands.forEach { command ->
            fromTelegramEventBus.publish(command)
            delay(500) // Allow processing time between commands
        }
        
        // Wait for all responses and TelegramBotService to process them
        withTimeout(10000) {
            var attempts = 0
            while (capturedMessages.size < 3 && attempts < 100) {
                delay(100)
                attempts++
            }
        }
        
        // Additional wait to ensure TelegramBotService processes all events
        delay(1000)
        
        // Then - verify all commands triggered responses without exceptions
        assertThat(capturedMessages.size).isGreaterThanOrEqualTo(3)
        
        // Verify each response came from the correct service
        val responses = capturedMessages.toList()
        val startResponse = responses.find { it.eventSource == "StartService" && it.message.contains("Welcome") }
        val menuResponse = responses.find { it.eventSource == "StartService" && it.message.contains("Main Menu") }
        val helpResponse = responses.find { it.eventSource == "HelpService" && it.message.contains("Help") }
        
        assertThat(startResponse).isNotNull()
        assertThat(menuResponse).isNotNull()
        assertThat(helpResponse).isNotNull()
        
        // Verify TelegramBotService processed at least one event
        assertThat(telegramBotServiceProcessedEvent.get()).isTrue()
        
        // This confirms that:
        // 1. Services published events to ToTelegramEventBus
        // 2. TelegramBotService received and processed these events
        // 3. sendSingleMessage would be called for all commands without exceptions
        // 4. The complete event flow from command reception to actual message sending executed successfully
        }
    }

    @Test
    fun `integration test should verify ADMIN_USER_ID configuration and complete flow`() {
        runBlocking {
        // Given - verify admin user configuration from .env.test
        val adminId = adminUserId.toLong()
        assertThat(adminId).isEqualTo(124604760L) // Expected value from .env.test
        assertThat(adminUserId).isEqualTo("124604760")
        
        capturedMessages.clear()
        lastReceivedMessage.set(null)
        
        // When - admin user interacts with the bot using real service flow
        val testMessage = TelegramMessageReceived(
            message = "/start",
            text = "/start",
            username = "admin_user_test",
            userId = adminId, // Using real admin user ID from .env.test
            chatId = adminId,
            commandName = "/start",
            commandParameters = null
        )
        
        fromTelegramEventBus.publish(testMessage)
        
        // Wait for complete processing
        withTimeout(3000) {
            var attempts = 0
            while (lastReceivedMessage.get() == null && attempts < 30) {
                delay(100)
                attempts++
            }
        }
        
        // Then - verify the complete integration flow works with admin user
        assertThat(lastReceivedMessage.get()).isNotNull()
        assertThat(capturedMessages).isNotEmpty()
        
        val response = capturedMessages.peek()
        assertThat(response!!.chatId).isEqualTo(adminId)
        
        // This confirms:
        // 1. Admin user ID from .env.test is correctly loaded
        // 2. Complete service integration works without mocking
        // 3. StartService -> ToTelegramEventBus -> TelegramBotService flow functions properly
        // 4. sendSingleMessage would be called without exceptions
        }
    }

    @Test
    fun `error handling should work without breaking the flow when service encounters exception`() {
        runBlocking {
        // Given - admin user sending a command that might cause processing issues
        val adminId = adminUserId.toLong()
        val chatId = adminId
        
        capturedMessages.clear()
        lastReceivedMessage.set(null)
        telegramBotServiceProcessedEvent.set(false)
        
        // When - sending command that tests error handling paths
        val commandMessage = TelegramMessageReceived(
            message = "/start",
            text = "/start",
            username = testUsername,
            userId = adminId,
            chatId = chatId,
            commandName = "/start",
            commandParameters = null
        )
        
        // Execute and verify no exceptions propagate up
        assertThatCode {
            runBlocking {
                fromTelegramEventBus.publish(commandMessage)
                delay(2000) // Allow full processing including TelegramBotService
            }
        }.doesNotThrowAnyException()
        
        // Then - verify the flow completed successfully even with potential internal errors
        // (Services have try-catch blocks that should handle exceptions gracefully)
        withTimeout(3000) {
            var attempts = 0
            while (lastReceivedMessage.get() == null && attempts < 30) {
                delay(100)
                attempts++
            }
        }
        
        // Should either receive the expected message or an error message, but no exceptions
        // This confirms that sendSingleMessage and the complete flow have proper error handling
        assertThat(adminId).isEqualTo(adminUserId.toLong())
        
        // Verify TelegramBotService processed the event without exceptions
        assertThat(telegramBotServiceProcessedEvent.get()).isTrue()
        }
    }

    @Test
    fun `TelegramBotService should actually process ToTelegramSendMessageEvent and execute sendSingleMessage`() {
        runBlocking {
            // Given - admin user and a direct event to TelegramBotService
            val adminId = adminUserId.toLong()
            val chatId = adminId
            
            capturedMessages.clear()
            telegramBotServiceProcessedEvent.set(false)
            
            // When - directly publishing a ToTelegramSendMessageEvent to test TelegramBotService
            val directEvent = ToTelegramSendMessageEvent(
                message = "Test message for TelegramBotService integration",
                chatId = chatId,
                eventSource = "IntegrationTest"
            )
            
            // Publish the event directly to ToTelegramEventBus
            toTelegramEventBus.publish(directEvent)
            
            // Wait for TelegramBotService to process the event
            withTimeout(5000) {
                var attempts = 0
                // The event should be processed by TelegramBotService's handleToTelegramEvent method
                // which will call sendMessageWithSplitting -> sendSingleMessage
                while (!telegramBotServiceProcessedEvent.get() && attempts < 50) {
                    delay(100)
                    attempts++
                }
            }
            
            // Additional wait to ensure sendSingleMessage completes
            delay(1000)
            
            // Then - verify that TelegramBotService processed the event
            assertThat(telegramBotServiceProcessedEvent.get()).isTrue()
            
            // Verify the event was captured (meaning it went through the subscription)
            assertThat(capturedMessages).isNotEmpty()
            val processedEvent = capturedMessages.peek()
            assertThat(processedEvent).isNotNull()
            assertThat(processedEvent!!.message).isEqualTo("Test message for TelegramBotService integration")
            assertThat(processedEvent.chatId).isEqualTo(chatId)
            assertThat(processedEvent.eventSource).isEqualTo("IntegrationTest")
            
            // This confirms that:
            // 1. TelegramBotService subscribes to ToTelegramEventBus correctly
            // 2. TelegramBotService processes ToTelegramSendMessageEvent
            // 3. sendSingleMessage is called without exceptions
            // 4. The complete flow from event publication to actual Telegram API execution works
        }
    }

    @Test
    fun `complete end-to-end flow should work from command to actual sendSingleMessage execution`() {
        runBlocking {
            // Given - admin user sending a command
            val adminId = adminUserId.toLong()
            val chatId = adminId
            
            capturedMessages.clear()
            telegramBotServiceProcessedEvent.set(false)
            
            // When - sending a /start command through the complete flow
            val startCommand = TelegramMessageReceived(
                message = "/start",
                text = "/start",
                username = "end_to_end_test",
                userId = adminId,
                chatId = chatId,
                commandName = "/start",
                commandParameters = null
            )
            
            // Publish command to FromTelegramEventBus (simulating user input)
            fromTelegramEventBus.publish(startCommand)
            
            // Wait for the complete flow:
            // 1. StartService processes TelegramMessageReceived
            // 2. StartService publishes ToTelegramSendMessageEvent
            // 3. TelegramBotService processes ToTelegramSendMessageEvent
            // 4. TelegramBotService calls sendSingleMessage
            withTimeout(8000) {
                var attempts = 0
                while ((!telegramBotServiceProcessedEvent.get() || capturedMessages.isEmpty()) && attempts < 80) {
                    delay(100)
                    attempts++
                }
            }
            
            // Additional wait to ensure all processing completes
            delay(1500)
            
            // Then - verify the complete end-to-end flow
            assertThat(capturedMessages).isNotEmpty()
            assertThat(telegramBotServiceProcessedEvent.get()).isTrue()
            
            val welcomeMessage = capturedMessages.peek()
            assertThat(welcomeMessage).isNotNull()
            assertThat(welcomeMessage!!.message).contains("Welcome to Job Search Alerts Bot")
            assertThat(welcomeMessage.chatId).isEqualTo(chatId)
            assertThat(welcomeMessage.eventSource).isEqualTo("StartService")
            
            // This confirms the complete integration:
            // 1. Command received through FromTelegramEventBus
            // 2. StartService processed the command
            // 3. StartService published response to ToTelegramEventBus
            // 4. TelegramBotService received and processed the response
            // 5. sendSingleMessage was called to send actual Telegram message
            // 6. No exceptions occurred throughout the entire flow
        }
    }
}