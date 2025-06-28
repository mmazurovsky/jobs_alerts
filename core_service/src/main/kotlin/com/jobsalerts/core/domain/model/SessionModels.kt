package com.jobsalerts.core.domain.model

// Command contexts - each major command has its own context
sealed class CommandContext {
    data object Idle : CommandContext()
    
    data class CreateAlert(val subContext: CreateAlertSubContext = CreateAlertSubContext.Initial) : CommandContext()
    data class SearchNow(val subContext: SearchNowSubContext = SearchNowSubContext.Initial) : CommandContext()
    data class ListAlerts(val subContext: ListAlertsSubContext = ListAlertsSubContext.ViewingList) : CommandContext()
    data class EditAlert(val subContext: EditAlertSubContext = EditAlertSubContext.SelectingAlert) : CommandContext()
    data class DeleteAlert(val subContext: DeleteAlertSubContext = DeleteAlertSubContext.SelectingAlert) : CommandContext()
}

// Subcontexts for CreateAlert command
sealed class CreateAlertSubContext {
    data object Initial : CreateAlertSubContext()
    data object CollectingDescription : CreateAlertSubContext()
    data object ConfirmingDetails : CreateAlertSubContext()
}

// Subcontexts for SearchNow command
sealed class SearchNowSubContext {
    data object Initial : SearchNowSubContext()
    data object CollectingDescription : SearchNowSubContext()
    data object ConfirmingDetails : SearchNowSubContext()
    data object ExecutingSearch : SearchNowSubContext()
}

// Subcontexts for ListAlerts command
sealed class ListAlertsSubContext {
    data object ViewingList : ListAlertsSubContext()
    data object SelectingAlert : ListAlertsSubContext()
}

// Subcontexts for EditAlert command
sealed class EditAlertSubContext {
    data object SelectingAlert : EditAlertSubContext()
    data object CollectingChanges : EditAlertSubContext()
    data object ConfirmingChanges : EditAlertSubContext()
}

// Subcontexts for DeleteAlert command
sealed class DeleteAlertSubContext {
    data object SelectingAlert : DeleteAlertSubContext()
    data object ConfirmingDeletion : DeleteAlertSubContext()
}

// Enhanced user session with command context
data class UserSession(
    val userId: Long,
    val chatId: Long,
    val username: String?,
    val context: CommandContext = CommandContext.Idle,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis(),
    val pendingJobSearch: JobSearchIn? = null,
    val retryCount: Int = 0,
    val selectedAlertId: String? = null, // For edit/delete operations
    val previousContext: CommandContext? = null // For context switching
)

// Session management interface
interface UserSessionManager {
    fun getSession(userId: Long, chatId: Long, username: String?): UserSession
    fun updateSession(userId: Long, update: (UserSession) -> UserSession)
    
    // Context management methods
    fun setContext(userId: Long, context: CommandContext)
    fun setSubContext(userId: Long, subContext: Any) // Any subcontext type
    fun resetToIdle(userId: Long)
    fun isInContext(userId: Long, contextType: Class<out CommandContext>): Boolean
    fun getCurrentContext(userId: Long): CommandContext
    fun getSubContext(userId: Long): Any?
} 