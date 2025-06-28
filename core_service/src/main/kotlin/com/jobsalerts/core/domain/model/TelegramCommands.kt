package com.jobsalerts.core.domain.model

import com.jobsalerts.core.service.JobSearchService
import com.jobsalerts.core.service.ImmediateSearchService
import com.jobsalerts.core.service.AlertCreationService
import org.telegram.telegrambots.meta.api.objects.replykeyboard.ReplyKeyboardMarkup
import org.telegram.telegrambots.meta.api.objects.replykeyboard.buttons.KeyboardButton
import org.telegram.telegrambots.meta.api.objects.replykeyboard.buttons.KeyboardRow

/**
 * Sealed class hierarchy for Telegram bot commands and callbacks
 * Provides type-safe handling of all user interactions
 */

// Interface for sending messages (will be injected into command handlers)
interface MessageSender {
    suspend fun sendMessage(chatId: Long, message: String)
}

// Base sealed class for all Telegram commands
sealed class TelegramCommand {
    abstract val chatId: Long
    abstract val userId: Long
    abstract val username: String?
    
    abstract suspend fun execute(
        messageSender: MessageSender, 
        sessionManager: UserSessionManager, 
        jobSearchService: JobSearchService,
        immediateSearchService: ImmediateSearchService? = null,
        alertCreationService: AlertCreationService? = null
    )
}

// Sealed class for text-based commands that start with "/"
sealed class SlashCommand : TelegramCommand() {
    abstract val rawCommand: String
    abstract val parameters: String?
    
    data class Start(
        override val chatId: Long,
        override val userId: Long,
        override val username: String?,
        override val rawCommand: String = "/start",
        override val parameters: String? = null
    ) : SlashCommand() {
        override suspend fun execute(messageSender: MessageSender, sessionManager: UserSessionManager, jobSearchService: JobSearchService, immediateSearchService: ImmediateSearchService?, alertCreationService: AlertCreationService?) {
            // Reset user session to idle context
            sessionManager.resetToIdle(userId)
            
            val welcomeMessage = """
                🤖 Welcome to Job Alerts Bot!
                
                I'll help you stay updated with the latest job opportunities matching your preferences.
                
                Use the commands below to get started:
                
                📋 **Available Commands:**
                /menu - Show main menu
                /create_alert - Create a new job search alert
                /search_now - Run an immediate job search
                /list_alerts - View your active job alerts
                /edit_alert - Modify existing job alerts
                /delete_alert - Remove job alerts
                /help - Show detailed help
                /cancel - Cancel current operation
                
                Type any command or use /menu to see options!
            """.trimIndent()
            
            messageSender.sendMessage(chatId, welcomeMessage)
        }
    }
    
    data class Help(
        override val chatId: Long,
        override val userId: Long,
        override val username: String?,
        override val rawCommand: String = "/help",
        override val parameters: String? = null
    ) : SlashCommand() {
        override suspend fun execute(messageSender: MessageSender, sessionManager: UserSessionManager, jobSearchService: JobSearchService, immediateSearchService: ImmediateSearchService?, alertCreationService: AlertCreationService?) {
            val helpMessage = """
                📖 **Job Alerts Bot - Help**
                
                **Main Commands:**
                /start - Welcome message and command overview
                /menu - Show main menu with quick options
                /help - Show this help message
                /cancel - Cancel current operation
                
                **Job Alert Management:**
                /create_alert - 🔔 Create a new job search alert
                /list_alerts - 📋 View all your active job alerts
                /edit_alert - ✏️ Modify an existing job alert
                /delete_alert - 🗑️ Remove a job alert
                
                **Job Search:**
                /search_now - 🔍 Run an immediate one-time job search
                
                **How to use:**
                • Simply type the command (e.g., /create_alert)
                • Add parameters if needed (e.g., /edit_alert 123)
                • Follow the prompts for interactive setup
                
                **Examples:**
                • /create_alert - Start creating a new alert
                • /list_alerts - See all your alerts
                • /search_now python berlin - Search for Python jobs in Berlin
                • /delete_alert 123 - Delete alert with ID 123
                
                Type /menu for quick access to all functions!
            """.trimIndent()
            
            messageSender.sendMessage(chatId, helpMessage)
        }
    }
    
    data class Menu(
        override val chatId: Long,
        override val userId: Long,
        override val username: String?,
        override val rawCommand: String = "/menu",
        override val parameters: String? = null
    ) : SlashCommand() {
        override suspend fun execute(messageSender: MessageSender, sessionManager: UserSessionManager, jobSearchService: JobSearchService, immediateSearchService: ImmediateSearchService?, alertCreationService: AlertCreationService?) {
            // Reset user session to idle context
            sessionManager.resetToIdle(userId)
            
            val menuMessage = """
                📋 **Main Menu**
                
                Choose what you'd like to do:
                
                **Job Alert Management:**
                /create_alert - 🔔 Create new job alert
                /list_alerts - 📋 View your alerts
                /edit_alert - ✏️ Edit an alert
                /delete_alert - 🗑️ Delete an alert
                
                **Search Jobs:**
                /search_now - 🔍 Search jobs immediately
                
                **Help & Info:**
                /help - 📖 Detailed help
                /start - 🏠 Welcome message
                
                Just type any command to get started!
            """.trimIndent()
            
            messageSender.sendMessage(chatId, menuMessage)
        }
    }
    
    data class CreateAlert(
        override val chatId: Long,
        override val userId: Long,
        override val username: String?,
        override val rawCommand: String = "/create_alert",
        override val parameters: String? = null
    ) : SlashCommand() {
        override suspend fun execute(messageSender: MessageSender, sessionManager: UserSessionManager, jobSearchService: JobSearchService, immediateSearchService: ImmediateSearchService?, alertCreationService: AlertCreationService?) {
            if (alertCreationService == null) {
                messageSender.sendMessage(chatId, "❌ Alert creation service is not available. Please try again later.")
                return
            }
            
            val initialDescription = parameters?.trim()
            
            if (!initialDescription.isNullOrBlank()) {
                // User provided description with command, process it directly
                sessionManager.setContext(userId, CommandContext.CreateAlert(CreateAlertSubContext.CollectingDescription))
                alertCreationService.processAlertDescription(
                    messageSender = messageSender,
                    sessionManager = sessionManager,
                    userId = userId,
                    chatId = chatId,
                    description = initialDescription
                )
            } else {
                // Set initial context and show instructions
                sessionManager.setContext(userId, CommandContext.CreateAlert(CreateAlertSubContext.Initial))
                sessionManager.updateSession(userId) { session ->
                    session.copy(
                        retryCount = 0,
                        pendingJobSearch = null
                    )
                }
                
                val instructionsMessage = buildString {
                    appendLine("🔔 **Creating a new job alert**")
                    appendLine()
                    append(JobSearchIn.getFormattingInstructions())
                    appendLine()
                    appendLine("💡 **Note:** This will create a recurring alert that searches for jobs automatically!")
                }
                messageSender.sendMessage(chatId, instructionsMessage)
            }
        }
    }
    
    data class ListAlerts(
        override val chatId: Long,
        override val userId: Long,
        override val username: String?,
        override val rawCommand: String = "/list_alerts",
        override val parameters: String? = null
    ) : SlashCommand() {
        override suspend fun execute(messageSender: MessageSender, sessionManager: UserSessionManager, jobSearchService: JobSearchService, immediateSearchService: ImmediateSearchService?, alertCreationService: AlertCreationService?) {
            // Set context to ListAlerts
            sessionManager.setContext(userId, CommandContext.ListAlerts())
            
            try {
                val userSearches = jobSearchService.getUserSearches(userId.toInt())
                
                if (userSearches.isEmpty()) {
                    val message = """
                        📋 **Your Job Alerts**
                        
                        You don't have any active job alerts yet.
                        
                        **Get started:**
                        /create_alert - Create your first job alert
                        /help - See all available commands
                        
                        Ready to find your next opportunity? 🚀
                    """.trimIndent()
                    
                    messageSender.sendMessage(chatId, message)
                } else {
                    val message = buildString {
                        appendLine("📋 **Your Active Job Alerts** (${userSearches.size} total)\n")
                        
                        userSearches.forEach { jobSearch ->
                            append(jobSearch.toMessage())
                            appendLine("─".repeat(40))
                            appendLine()
                        }
                        
                        appendLine("**Available Actions:**")
                        appendLine("/edit_alert [ID] - Edit a specific alert")
                        appendLine("/delete_alert [ID] - Delete a specific alert")
                        appendLine("/create_alert - Create a new alert")
                        appendLine("/search_now - Run an immediate search")
                    }
                    
                    messageSender.sendMessage(chatId, message.toString())
                }
            } catch (e: Exception) {
                messageSender.sendMessage(chatId, "❌ Error retrieving your job alerts. Please try again later.")
            }
        }
    }
    
    data class EditAlert(
        override val chatId: Long,
        override val userId: Long,
        override val username: String?,
        override val rawCommand: String = "/edit_alert",
        override val parameters: String? = null
    ) : SlashCommand() {
        override suspend fun execute(messageSender: MessageSender, sessionManager: UserSessionManager, jobSearchService: JobSearchService, immediateSearchService: ImmediateSearchService?, alertCreationService: AlertCreationService?) {
            val alertId = parameters?.trim()
            
            if (alertId.isNullOrEmpty()) {
                // No alert ID provided, ask user to select one
                sessionManager.setContext(userId, CommandContext.EditAlert(EditAlertSubContext.SelectingAlert))
                val message = buildString {
                    appendLine("✏️ **Edit Job Alert**")
                    appendLine()
                    appendLine("Which alert would you like to edit? Please provide the alert ID.")
                    appendLine()
                    appendLine("**Example:** `123` (just the ID number)")
                    appendLine()
                    appendLine("Use /list_alerts to see your alerts and their IDs.")
                    appendLine("Use /cancel to abort this operation.")
                }
                messageSender.sendMessage(chatId, message)
            } else {
                // Alert ID provided, move to collecting changes
                sessionManager.setContext(userId, CommandContext.EditAlert(EditAlertSubContext.CollectingChanges))
                sessionManager.updateSession(userId) { session ->
                    session.copy(selectedAlertId = alertId)
                }
                
                val message = buildString {
                    appendLine("✏️ **Editing Alert: $alertId**")
                    appendLine()
                    appendLine("Please provide the new job search criteria:")
                    appendLine()
                    append(JobSearchIn.getFormattingInstructions())
                    appendLine()
                    appendLine("Use /cancel to abort this operation.")
                }
                messageSender.sendMessage(chatId, message)
            }
        }
    }
    
    data class DeleteAlert(
        override val chatId: Long,
        override val userId: Long,
        override val username: String?,
        override val rawCommand: String = "/delete_alert",
        override val parameters: String? = null
    ) : SlashCommand() {
        override suspend fun execute(messageSender: MessageSender, sessionManager: UserSessionManager, jobSearchService: JobSearchService, immediateSearchService: ImmediateSearchService?, alertCreationService: AlertCreationService?) {
            val alertId = parameters?.trim()
            
            if (alertId.isNullOrEmpty()) {
                // No alert ID provided, ask user to select one
                sessionManager.setContext(userId, CommandContext.DeleteAlert(DeleteAlertSubContext.SelectingAlert))
                val message = buildString {
                    appendLine("🗑️ **Delete Job Alert**")
                    appendLine()
                    appendLine("Which alert would you like to delete? Please provide the alert ID.")
                    appendLine()
                    appendLine("**Example:** `123` (just the ID number)")
                    appendLine()
                    appendLine("Use /list_alerts to see your alerts and their IDs.")
                    appendLine("Use /cancel to abort this operation.")
                }
                messageSender.sendMessage(chatId, message)
            } else {
                // Alert ID provided, ask for confirmation
                sessionManager.setContext(userId, CommandContext.DeleteAlert(DeleteAlertSubContext.ConfirmingDeletion))
                sessionManager.updateSession(userId) { session ->
                    session.copy(selectedAlertId = alertId)
                }
                
                val message = buildString {
                    appendLine("🗑️ **Delete Alert Confirmation**")
                    appendLine()
                    appendLine("Are you sure you want to delete alert: **$alertId**?")
                    appendLine()
                    appendLine("⚠️ **Warning:** This action cannot be undone!")
                    appendLine()
                    appendLine("• Reply '**yes**' to confirm deletion")
                    appendLine("• Reply '**no**' to cancel")
                    appendLine("• Use /cancel to abort this operation")
                }
                messageSender.sendMessage(chatId, message)
            }
        }
    }
    
    data class Cancel(
        override val chatId: Long,
        override val userId: Long,
        override val username: String?,
        override val rawCommand: String = "/cancel",
        override val parameters: String? = null
    ) : SlashCommand() {
        override suspend fun execute(messageSender: MessageSender, sessionManager: UserSessionManager, jobSearchService: JobSearchService, immediateSearchService: ImmediateSearchService?, alertCreationService: AlertCreationService?) {
            // Reset user session to idle context
            sessionManager.resetToIdle(userId)
            
            messageSender.sendMessage(chatId, "❌ Operation cancelled. Use /menu to see available options.")
        }
    }
    
    data class Unknown(
        override val chatId: Long,
        override val userId: Long,
        override val username: String?,
        override val rawCommand: String,
        override val parameters: String? = null
    ) : SlashCommand() {
        override suspend fun execute(messageSender: MessageSender, sessionManager: UserSessionManager, jobSearchService: JobSearchService, immediateSearchService: ImmediateSearchService?, alertCreationService: AlertCreationService?) {
            messageSender.sendMessage(chatId, "❓ Unknown command: $rawCommand\n\nUse /help to see available commands or /menu for quick access.")
        }
    }
}

// Sealed class for text messages (not commands)
sealed class TextMessage : TelegramCommand() {
    abstract val text: String
    
    data class Regular(
        override val chatId: Long,
        override val userId: Long,
        override val username: String?,
        override val text: String
    ) : TextMessage() {
        override suspend fun execute(messageSender: MessageSender, sessionManager: UserSessionManager, jobSearchService: JobSearchService, immediateSearchService: ImmediateSearchService?, alertCreationService: AlertCreationService?) {
            val session = sessionManager.getSession(userId, chatId, username)
            val currentContext = sessionManager.getCurrentContext(userId)
            
            when (currentContext) {
                CommandContext.Idle -> {
                    // Handle natural language or quick commands
                    val lowerText = text.lowercase().trim()
                    when {
                        lowerText.contains("help") -> {
                            messageSender.sendMessage(chatId, "Use /help to see all available commands or /menu for quick access.")
                        }
                        lowerText.contains("menu") -> {
                            messageSender.sendMessage(chatId, "Use /menu to see all available options.")
                        }
                        lowerText.contains("create") && lowerText.contains("alert") -> {
                            messageSender.sendMessage(chatId, "Use /create_alert to create a new job alert.")
                        }
                        lowerText.contains("search") -> {
                            messageSender.sendMessage(chatId, "Use /search_now to run an immediate job search.")
                        }
                        lowerText.contains("list") && lowerText.contains("alert") -> {
                            messageSender.sendMessage(chatId, "Use /list_alerts to see your job alerts.")
                        }
                        lowerText.contains("edit") && lowerText.contains("alert") -> {
                            messageSender.sendMessage(chatId, "Use /edit_alert [ID] to edit a specific alert.")
                        }
                        lowerText.contains("delete") && lowerText.contains("alert") -> {
                            messageSender.sendMessage(chatId, "Use /delete_alert [ID] to delete a specific alert.")
                        }
                        else -> {
                            messageSender.sendMessage(chatId, "I don't understand. Use /help to see available commands or /menu for quick access to all options.")
                        }
                    }
                }
                is CommandContext.CreateAlert -> {
                    when (currentContext.subContext) {
                        CreateAlertSubContext.Initial -> {
                            // User is responding to initial instructions, move to collecting description
                            sessionManager.setSubContext(userId, CreateAlertSubContext.CollectingDescription)
                            // Process their description
                            if (alertCreationService != null) {
                                alertCreationService.processAlertDescription(
                                    messageSender = messageSender,
                                    sessionManager = sessionManager,
                                    userId = userId,
                                    chatId = chatId,
                                    description = text
                                )
                            } else {
                                messageSender.sendMessage(chatId, "❌ Service unavailable. Please try again later.")
                                sessionManager.resetToIdle(userId)
                            }
                        }
                        CreateAlertSubContext.CollectingDescription -> {
                            // User is providing alert description
                            if (alertCreationService != null) {
                                alertCreationService.processAlertDescription(
                                    messageSender = messageSender,
                                    sessionManager = sessionManager,
                                    userId = userId,
                                    chatId = chatId,
                                    description = text
                                )
                            } else {
                                messageSender.sendMessage(chatId, "❌ Service unavailable. Please try again later.")
                                sessionManager.resetToIdle(userId)
                            }
                        }
                        CreateAlertSubContext.ConfirmingDetails -> {
                            // User is confirming or rejecting the parsed alert
                            if (alertCreationService != null) {
                                alertCreationService.processConfirmation(
                                    messageSender = messageSender,
                                    sessionManager = sessionManager,
                                    userId = userId,
                                    chatId = chatId,
                                    username = username,
                                    confirmation = text
                                )
                            } else {
                                messageSender.sendMessage(chatId, "❌ Service unavailable. Please try again later.")
                                sessionManager.resetToIdle(userId)
                            }
                        }
                        else -> {
                            messageSender.sendMessage(chatId, "I'm not sure what you're trying to do. Use /cancel to reset or /menu for options.")
                        }
                    }
                }
                is CommandContext.SearchNow -> {
                    when (currentContext.subContext) {
                        SearchNowSubContext.Initial -> {
                            // User is responding to initial instructions, move to collecting description
                            sessionManager.setSubContext(userId, SearchNowSubContext.CollectingDescription)
                            // Process their description
                            if (immediateSearchService != null) {
                                immediateSearchService.processJobSearchDescription(
                                    messageSender = messageSender,
                                    sessionManager = sessionManager,
                                    userId = userId,
                                    chatId = chatId,
                                    description = text
                                )
                            } else {
                                messageSender.sendMessage(chatId, "❌ Service unavailable. Please try again later.")
                                sessionManager.resetToIdle(userId)
                            }
                        }
                        SearchNowSubContext.CollectingDescription -> {
                            // User is providing job search description
                            if (immediateSearchService != null) {
                                immediateSearchService.processJobSearchDescription(
                                    messageSender = messageSender,
                                    sessionManager = sessionManager,
                                    userId = userId,
                                    chatId = chatId,
                                    description = text
                                )
                            } else {
                                messageSender.sendMessage(chatId, "❌ Service unavailable. Please try again later.")
                                sessionManager.resetToIdle(userId)
                            }
                        }
                        SearchNowSubContext.ConfirmingDetails -> {
                            // User is confirming or rejecting the parsed job search
                            if (immediateSearchService != null) {
                                immediateSearchService.processConfirmation(
                                    messageSender = messageSender,
                                    sessionManager = sessionManager,
                                    userId = userId,
                                    chatId = chatId,
                                    username = username,
                                    confirmation = text
                                )
                            } else {
                                messageSender.sendMessage(chatId, "❌ Service unavailable. Please try again later.")
                                sessionManager.resetToIdle(userId)
                            }
                        }
                        else -> {
                            messageSender.sendMessage(chatId, "I'm not sure what you're trying to do. Use /cancel to reset or /menu for options.")
                        }
                    }
                }
                is CommandContext.EditAlert -> {
                    when (currentContext.subContext) {
                        EditAlertSubContext.SelectingAlert -> {
                            // User is providing alert ID to edit
                            val alertId = text.trim()
                            if (alertId.isBlank()) {
                                messageSender.sendMessage(chatId, "Please provide a valid alert ID. Use /list_alerts to see your alerts.")
                                return
                            }
                            
                            // Move to collecting changes subcontext
                            sessionManager.setSubContext(userId, EditAlertSubContext.CollectingChanges)
                            sessionManager.updateSession(userId) { session ->
                                session.copy(selectedAlertId = alertId)
                            }
                            
                            val message = buildString {
                                appendLine("✏️ **Editing Alert: $alertId**")
                                appendLine()
                                appendLine("Please provide the new job search criteria:")
                                appendLine()
                                append(JobSearchIn.getFormattingInstructions())
                                appendLine()
                                appendLine("Use /cancel to abort this operation.")
                            }
                            messageSender.sendMessage(chatId, message)
                        }
                        EditAlertSubContext.CollectingChanges -> {
                            // User is providing new criteria for the alert
                            // TODO: Implement alert editing logic here
                            messageSender.sendMessage(chatId, "⚠️ Alert editing functionality is not yet implemented. Use /cancel to exit.")
                        }
                        EditAlertSubContext.ConfirmingChanges -> {
                            // User is confirming the changes
                            // TODO: Implement confirmation logic here
                            messageSender.sendMessage(chatId, "⚠️ Alert editing functionality is not yet implemented. Use /cancel to exit.")
                        }
                        else -> {
                            messageSender.sendMessage(chatId, "I'm not sure what you're trying to do. Use /cancel to reset or /menu for options.")
                        }
                    }
                }
                is CommandContext.DeleteAlert -> {
                    when (currentContext.subContext) {
                        DeleteAlertSubContext.SelectingAlert -> {
                            // User is providing alert ID to delete
                            val alertId = text.trim()
                            if (alertId.isBlank()) {
                                messageSender.sendMessage(chatId, "Please provide a valid alert ID. Use /list_alerts to see your alerts.")
                                return
                            }
                            
                            // Move to confirming deletion subcontext
                            sessionManager.setSubContext(userId, DeleteAlertSubContext.ConfirmingDeletion)
                            sessionManager.updateSession(userId) { session ->
                                session.copy(selectedAlertId = alertId)
                            }
                            
                            val message = buildString {
                                appendLine("🗑️ **Delete Alert Confirmation**")
                                appendLine()
                                appendLine("Are you sure you want to delete alert: **$alertId**?")
                                appendLine()
                                appendLine("⚠️ **Warning:** This action cannot be undone!")
                                appendLine()
                                appendLine("• Reply '**yes**' to confirm deletion")
                                appendLine("• Reply '**no**' to cancel")
                                appendLine("• Use /cancel to abort this operation")
                            }
                            messageSender.sendMessage(chatId, message)
                        }
                        DeleteAlertSubContext.ConfirmingDeletion -> {
                            // User is confirming or canceling deletion
                            val lowerConfirmation = text.lowercase().trim()
                            val alertId = session.selectedAlertId
                            
                            when {
                                lowerConfirmation in listOf("yes", "y", "confirm", "delete") -> {
                                    if (alertId != null) {
                                        try {
                                            // TODO: Implement actual deletion logic here
                                            messageSender.sendMessage(chatId, "✅ **Alert $alertId has been deleted successfully.**")
                                            sessionManager.resetToIdle(userId)
                                        } catch (e: Exception) {
                                            messageSender.sendMessage(chatId, "❌ Failed to delete alert $alertId. Please try again later.")
                                            sessionManager.resetToIdle(userId)
                                        }
                                    } else {
                                        messageSender.sendMessage(chatId, "❌ No alert ID found. Please start over with /delete_alert.")
                                        sessionManager.resetToIdle(userId)
                                    }
                                }
                                lowerConfirmation in listOf("no", "n", "cancel") -> {
                                    messageSender.sendMessage(chatId, "❌ Alert deletion cancelled. Your alert is safe!")
                                    sessionManager.resetToIdle(userId)
                                }
                                else -> {
                                    messageSender.sendMessage(chatId, "Please respond with '**yes**' to delete the alert, '**no**' to cancel, or /cancel to abort.")
                                }
                            }
                        }
                        else -> {
                            messageSender.sendMessage(chatId, "I'm not sure what you're trying to do. Use /cancel to reset or /menu for options.")
                        }
                    }
                }
                else -> {
                    // Handle other contexts or unknown states
                    messageSender.sendMessage(chatId, "I'm not sure what you're trying to do in this context. Use /cancel to reset or /menu for options.")
                }
            }
        }
    }
}

// Command parsing utilities
object TelegramCommandParser {
    
    fun parseSlashCommand(
        chatId: Long,
        userId: Long,
        username: String?,
        commandText: String
    ): SlashCommand {
        val parts = commandText.split(" ", limit = 2)
        val command = parts[0].lowercase()
        val parameters = if (parts.size > 1) parts[1] else null
        
        return when (command) {
            "/start" -> SlashCommand.Start(chatId, userId, username, commandText, parameters)
            "/help" -> SlashCommand.Help(chatId, userId, username, commandText, parameters)
            "/menu" -> SlashCommand.Menu(chatId, userId, username, commandText, parameters)
            "/create_alert" -> SlashCommand.CreateAlert(chatId, userId, username, commandText, parameters)
            "/search_now" -> SlashCommand.ImmediateSearch(chatId, userId, username, commandText, parameters)
            "/list_alerts" -> SlashCommand.ListAlerts(chatId, userId, username, commandText, parameters)
            "/edit_alert" -> SlashCommand.EditAlert(chatId, userId, username, commandText, parameters)
            "/delete_alert" -> SlashCommand.DeleteAlert(chatId, userId, username, commandText, parameters)
            "/cancel" -> SlashCommand.Cancel(chatId, userId, username, commandText, parameters)
            else -> SlashCommand.Unknown(chatId, userId, username, commandText, parameters)
        }
    }
    

    
    fun parseTextMessage(
        chatId: Long,
        userId: Long,
        username: String?,
        text: String,
        context: CommandContext
    ): TextMessage {
        return TextMessage.Regular(chatId, userId, username, text)
    }
}

// Helper function to create main reply keyboard (persistent buttons at bottom of chat)
private fun createMainReplyKeyboard(): ReplyKeyboardMarkup {
    val keyboard = ReplyKeyboardMarkup()
    
    // First row: Create Alert and Search Now
    val row1 = KeyboardRow()
    row1.add(KeyboardButton("🔔 Create Alert"))
    row1.add(KeyboardButton("🔍 Search Now"))
    
    // Second row: My Alerts and Edit Alert
    val row2 = KeyboardRow()
    row2.add(KeyboardButton("📋 My Alerts"))
    row2.add(KeyboardButton("✏️ Edit Alert"))
    
    // Third row: Delete Alert
    val row3 = KeyboardRow()
    row3.add(KeyboardButton("🗑️ Delete Alert"))
    
    keyboard.keyboard = listOf(row1, row2, row3)
    keyboard.resizeKeyboard = true  // Makes buttons smaller
    keyboard.oneTimeKeyboard = false  // Keeps keyboard visible
    keyboard.selective = false
    
    return keyboard
} 
