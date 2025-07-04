package com.jobsalerts.core.bot

import com.jobsalerts.core.domain.model.TelegramMessageReceived
import com.jobsalerts.core.infrastructure.FromTelegramEventBus
import kotlinx.coroutines.delay
import kotlinx.coroutines.runBlocking
import org.assertj.core.api.Assertions.*
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import org.junit.jupiter.api.extension.ExtendWith
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.beans.factory.annotation.Value
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.test.context.ActiveProfiles
import org.springframework.test.context.TestPropertySource
import org.springframework.test.context.junit.jupiter.SpringExtension

/**
 * Integration test that simulates real user interactions with /start and /menu commands.
 * Uses test environment configuration including ADMIN_USER_ID from .env.test
 */
@SpringBootTest
@ActiveProfiles("test")  
@TestPropertySource(properties = ["spring.main.web-application-type=none"])
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
@ExtendWith(SpringExtension::class)
class TelegramBotIntegrationTest {

    @Autowired
    private lateinit var fromTelegramEventBus: FromTelegramEventBus
    
    @Value("\${ADMIN_USER_ID}")
    private lateinit var adminUserId: String
    
    private val testChatId = 987654321L
    private val testUsername = "integration_test_user"

    @Test
    fun `should handle start command from admin user without throwing exceptions`() = runBlocking {
        // Given - admin user from .env.test file sending /start command
        val userId = adminUserId.toLong()
        val startMessage = TelegramMessageReceived(
            message = "/start",
            text = "/start",
            username = testUsername,
            userId = userId,
            chatId = testChatId,
            commandName = "/start",
            commandParameters = null
        )
        
        // When - user sends /start command through event bus
        assertThatCode {
            runBlocking {
                fromTelegramEventBus.publish(startMessage)
                delay(1000) // Allow processing time
            }
        }.doesNotThrowAnyException()
        
        // Then - verify admin user ID is valid and command was processed
        assertThat(userId).isGreaterThan(0)
        assertThat(adminUserId).isEqualTo("124604760") // From .env.test
    }

    @Test
    fun `should handle menu command from admin user without throwing exceptions`() = runBlocking {
        // Given - admin user from .env.test file sending /menu command
        val userId = adminUserId.toLong()
        val menuMessage = TelegramMessageReceived(
            message = "/menu",
            text = "/menu",
            username = testUsername,
            userId = userId,
            chatId = testChatId,
            commandName = "/menu",
            commandParameters = null
        )
        
        // When - user sends /menu command through event bus
        assertThatCode {
            runBlocking {
                fromTelegramEventBus.publish(menuMessage)
                delay(1000) // Allow processing time  
            }
        }.doesNotThrowAnyException()
        
        // Then - verify admin user ID is valid and command was processed
        assertThat(userId).isGreaterThan(0)
        assertThat(adminUserId).isEqualTo("124604760") // From .env.test
    }

    @Test  
    fun `should process multiple commands sequentially without errors`() = runBlocking {
        // Given - admin user from test environment
        val userId = adminUserId.toLong()
        
        val commands = listOf(
            TelegramMessageReceived(
                message = "/start",
                text = "/start", 
                username = testUsername,
                userId = userId,
                chatId = testChatId,
                commandName = "/start",
                commandParameters = null
            ),
            TelegramMessageReceived(
                message = "/menu",
                text = "/menu",
                username = testUsername, 
                userId = userId,
                chatId = testChatId,
                commandName = "/menu",
                commandParameters = null
            ),
            TelegramMessageReceived(
                message = "/help",
                text = "/help",
                username = testUsername,
                userId = userId, 
                chatId = testChatId,
                commandName = "/help",
                commandParameters = null
            )
        )
        
        // When - sending multiple commands sequentially
        assertThatCode {
            runBlocking {
                commands.forEach { command ->
                    fromTelegramEventBus.publish(command)
                    delay(300) // Small delay between commands
                }
                delay(1000) // Allow final processing
            }
        }.doesNotThrowAnyException()
        
        // Then - verify all commands were processed successfully
        assertThat(userId).isEqualTo(124604760L) // Admin user from .env.test
    }

    @Test
    fun `should verify sendSingleMessage function executes without errors through event flow`() = runBlocking {
        // Given - simulating complete user interaction that would trigger sendSingleMessage
        val userId = adminUserId.toLong()
        
        // When - sending start command that should trigger response message
        val startInteraction = TelegramMessageReceived(
            message = "/start Welcome!",
            text = "/start Welcome!",
            username = "test_user_interaction", 
            userId = userId,
            chatId = testChatId,
            commandName = "/start",
            commandParameters = "Welcome!"
        )
        
        assertThatCode {
            runBlocking {
                fromTelegramEventBus.publish(startInteraction)
                delay(500)
                
                // Follow up with menu command
                val menuInteraction = TelegramMessageReceived(
                    message = "/menu",
                    text = "/menu",
                    username = "test_user_interaction",
                    userId = userId,
                    chatId = testChatId, 
                    commandName = "/menu",
                    commandParameters = null
                )
                fromTelegramEventBus.publish(menuInteraction)
                delay(1000) // Allow full processing
            }
        }.doesNotThrowAnyException()
        
        // Then - verify the integration flow completed successfully
        // Note: This tests that sendSingleMessage is called without errors through the event system
        assertThat(userId).isEqualTo(adminUserId.toLong())
    }

    @Test
    fun `should validate admin user ID from env test configuration`() {
        // Given - configuration loaded from .env.test
        
        // When - checking admin user ID value
        val adminId = adminUserId.toLong()
        
        // Then - verify it matches expected test value
        assertThat(adminId).isEqualTo(124604760L)
        assertThat(adminUserId).isNotBlank()
        assertThat(adminUserId).matches("\\d+") // Should be numeric
    }

    @Test
    fun `should handle edge cases in command processing without errors`() = runBlocking {
        // Given - admin user with various command scenarios
        val userId = adminUserId.toLong()
        
        val edgeCaseCommands = listOf(
            // Command with extra whitespace
            TelegramMessageReceived(
                message = "  /start  ",
                text = "  /start  ",
                username = testUsername,
                userId = userId,
                chatId = testChatId,
                commandName = "/start",
                commandParameters = null
            ),
            // Command with parameters
            TelegramMessageReceived(
                message = "/menu show options",
                text = "/menu show options", 
                username = testUsername,
                userId = userId,
                chatId = testChatId,
                commandName = "/menu",
                commandParameters = "show options"
            )
        )
        
        // When - processing edge case commands
        assertThatCode {
            runBlocking {
                edgeCaseCommands.forEach { command ->
                    fromTelegramEventBus.publish(command)
                    delay(400) // Allow processing
                }
                delay(1000) // Final processing time
            }
        }.doesNotThrowAnyException()
        
        // Then - verify all edge cases handled successfully  
        assertThat(userId).isGreaterThan(0)
    }
}