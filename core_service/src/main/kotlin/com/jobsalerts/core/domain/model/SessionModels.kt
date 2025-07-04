package com.jobsalerts.core.domain.model

// Command contexts - each major command has its own context
interface CommandContext {}

data object IdleCommandContext : CommandContext

// Subcontexts for CreateAlert command
sealed class CreateAlertSubContext: CommandContext {
    data object Initial : CreateAlertSubContext()
    data object CollectingDescription : CreateAlertSubContext()
    data object ConfirmingDetails : CreateAlertSubContext()
} 

// Subcontexts for SearchNow command
sealed class SearchNowSubContext : CommandContext {
    data object Initial : SearchNowSubContext()
    data object CollectingDescription : SearchNowSubContext()
    data object ConfirmingDetails : SearchNowSubContext()
    data object ExecutingSearch : SearchNowSubContext()
}

// Subcontexts for ListAlerts command
sealed class ListAlertsSubContext : CommandContext {
    data object ViewingList : ListAlertsSubContext()
    data object SelectingAlert : ListAlertsSubContext()
}

// Subcontexts for EditAlert command
sealed class EditAlertSubContext : CommandContext {
    data object SelectingAlert : EditAlertSubContext()
    data object CollectingChanges : EditAlertSubContext()
    data object ConfirmingChanges : EditAlertSubContext()
}

// Subcontexts for DeleteAlert command
sealed class DeleteAlertSubContext : CommandContext {
    data object SelectingAlert : DeleteAlertSubContext()
    data object ConfirmingDeletion : DeleteAlertSubContext()
}

// Subcontexts for Help command
sealed class HelpSubContext : CommandContext {
    data object ShowingHelp : HelpSubContext()
}

// Subcontexts for Start command
sealed class StartSubContext : CommandContext {
    data object ShowingWelcome : StartSubContext()
}

// Enhanced user session with command context
data class UserSession(
    val userId: Long,
    val chatId: Long,
    val username: String? = null,
    val context: CommandContext = IdleCommandContext,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis(),
    val pendingJobSearch: JobSearchIn? = null,
    val retryCount: Int = 0,
    val selectedAlertId: String? = null, // For edit/delete operations
    val previousContext: CommandContext? = null // For context switching
)

// Session management interface
