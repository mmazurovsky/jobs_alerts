package com.jobsalerts.core.service

import com.jobsalerts.core.domain.model.*
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.stereotype.Service
import java.util.concurrent.ConcurrentHashMap

@Service
class SessionManager : UserSessionManager, Logging {
    
    private val userSessions = ConcurrentHashMap<Long, UserSession>()
    
    override fun getSession(userId: Long, chatId: Long, username: String?): UserSession {
        return userSessions.computeIfAbsent(userId) { 
            UserSession(userId, chatId, username)
        }
    }
    
    override fun updateSession(userId: Long, update: (UserSession) -> UserSession) {
        userSessions.compute(userId) { _, existingSession ->
            if (existingSession != null) {
                update(existingSession).copy(updatedAt = System.currentTimeMillis())
            } else {
                logger.warn { "Attempted to update non-existent session for user $userId" }
                existingSession
            }
        }
    }
    
    override fun setContext(userId: Long, context: CommandContext) {
        logger.debug { "Setting context for user $userId to: $context" }
        updateSession(userId) { session ->
            session.copy(
                previousContext = session.context,
                context = context
            )
        }
    }
    
    override fun setSubContext(userId: Long, subContext: Any) {
        logger.debug { "Setting subcontext for user $userId to: $subContext" }
        updateSession(userId) { session ->
            val newContext = when (session.context) {
                is CommandContext.CreateAlert -> {
                    if (subContext is CreateAlertSubContext) {
                        session.context.copy(subContext = subContext)
                    } else {
                        logger.warn { "Invalid subcontext type for CreateAlert: $subContext" }
                        session.context
                    }
                }
                is CommandContext.SearchNow -> {
                    if (subContext is SearchNowSubContext) {
                        session.context.copy(subContext = subContext)
                    } else {
                        logger.warn { "Invalid subcontext type for SearchNow: $subContext" }
                        session.context
                    }
                }
                is CommandContext.ListAlerts -> {
                    if (subContext is ListAlertsSubContext) {
                        session.context.copy(subContext = subContext)
                    } else {
                        logger.warn { "Invalid subcontext type for ListAlerts: $subContext" }
                        session.context
                    }
                }
                is CommandContext.EditAlert -> {
                    if (subContext is EditAlertSubContext) {
                        session.context.copy(subContext = subContext)
                    } else {
                        logger.warn { "Invalid subcontext type for EditAlert: $subContext" }
                        session.context
                    }
                }
                is CommandContext.DeleteAlert -> {
                    if (subContext is DeleteAlertSubContext) {
                        session.context.copy(subContext = subContext)
                    } else {
                        logger.warn { "Invalid subcontext type for DeleteAlert: $subContext" }
                        session.context
                    }
                }
                else -> {
                    logger.warn { "Cannot set subcontext $subContext for context ${session.context}" }
                    session.context
                }
            }
            session.copy(context = newContext)
        }
    }
    
    override fun resetToIdle(userId: Long) {
        logger.debug { "Resetting user $userId to idle context" }
        updateSession(userId) { session ->
            session.copy(
                context = CommandContext.Idle,
                pendingJobSearch = null,
                retryCount = 0,
                selectedAlertId = null,
                previousContext = session.context
            )
        }
    }
    
    override fun isInContext(userId: Long, contextType: Class<out CommandContext>): Boolean {
        val session = userSessions[userId] ?: return false
        return contextType.isInstance(session.context)
    }
    
    override fun getCurrentContext(userId: Long): CommandContext {
        return userSessions[userId]?.context ?: CommandContext.Idle
    }
    
    override fun getSubContext(userId: Long): Any? {
        val session = userSessions[userId] ?: return null
        return when (val context = session.context) {
            is CommandContext.CreateAlert -> context.subContext
            is CommandContext.SearchNow -> context.subContext
            is CommandContext.ListAlerts -> context.subContext
            is CommandContext.EditAlert -> context.subContext
            is CommandContext.DeleteAlert -> context.subContext
            else -> null
        }
    }
    
    // Convenience methods for specific contexts
    fun setCreateAlertContext(userId: Long, subContext: CreateAlertSubContext = CreateAlertSubContext.Initial) {
        setContext(userId, CommandContext.CreateAlert(subContext))
    }
    
    fun setSearchNowContext(userId: Long, subContext: SearchNowSubContext = SearchNowSubContext.Initial) {
        setContext(userId, CommandContext.SearchNow(subContext))
    }
    
    fun setListAlertsContext(userId: Long, subContext: ListAlertsSubContext = ListAlertsSubContext.ViewingList) {
        setContext(userId, CommandContext.ListAlerts(subContext))
    }
    
    fun setEditAlertContext(userId: Long, alertId: String? = null, subContext: EditAlertSubContext = EditAlertSubContext.SelectingAlert) {
        setContext(userId, CommandContext.EditAlert(subContext))
        if (alertId != null) {
            updateSession(userId) { session ->
                session.copy(selectedAlertId = alertId)
            }
        }
    }
    
    fun setDeleteAlertContext(userId: Long, alertId: String? = null, subContext: DeleteAlertSubContext = DeleteAlertSubContext.SelectingAlert) {
        setContext(userId, CommandContext.DeleteAlert(subContext))
        if (alertId != null) {
            updateSession(userId) { session ->
                session.copy(selectedAlertId = alertId)
            }
        }
    }
    
    // Helper method to check if user is in specific subcontext
    fun isInSubContext(userId: Long, subContextType: Class<*>): Boolean {
        val subContext = getSubContext(userId) ?: return false
        return subContextType.isInstance(subContext)
    }
    
    // Debugging method to get session info
    fun getSessionInfo(userId: Long): String {
        val session = userSessions[userId] ?: return "No session found"
        return buildString {
            appendLine("User: $userId")
            appendLine("Context: ${session.context}")
            appendLine("SubContext: ${getSubContext(userId)}")
            appendLine("Selected Alert ID: ${session.selectedAlertId}")
            appendLine("Pending Job Search: ${session.pendingJobSearch?.jobTitle ?: "None"}")
            appendLine("Retry Count: ${session.retryCount}")
            appendLine("Previous Context: ${session.previousContext}")
        }
    }
} 