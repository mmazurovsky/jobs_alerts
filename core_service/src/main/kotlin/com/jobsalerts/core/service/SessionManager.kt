package com.jobsalerts.core.service

import com.jobsalerts.core.domain.model.*
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.stereotype.Service
import java.util.concurrent.ConcurrentHashMap

interface UserSessionManager {
    fun getSession(userId: Long, chatId: Long, username: String?): UserSession
    fun updateSession(userId: Long, update: (UserSession) -> UserSession)
    fun setContext(chatId: Long, userId: Long, context: CommandContext)
    fun resetToIdle(userId: Long)
    fun isInContext(userId: Long, contextType: Class<out CommandContext>): Boolean
    fun getCurrentContext(userId: Long): CommandContext
} 

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
    
    override fun setContext(chatId: Long, userId: Long, context: CommandContext) {
        val previousContext = getCurrentContext(userId)
        logger.info { "📋 SessionManager: Setting context for user $userId from '$previousContext' to '$context'" }
        
        // Ensure session exists or create it, similar to getSession
        userSessions.compute(userId) { _, existingSession ->
            if (existingSession != null) {
                existingSession.copy(
                    previousContext = existingSession.context,
                    context = context,
                    updatedAt = System.currentTimeMillis()
                )
            } else {
                logger.info { "📋 SessionManager: Creating new session for user $userId with context $context" }
                UserSession(
                    userId = userId,
                    chatId = chatId, 
                    context = context
                )
            }
        }
        
        logger.info { "📋 SessionManager: Context successfully set for user $userId to '$context'" }
    }
        
    override fun resetToIdle(userId: Long) {
        val previousContext = getCurrentContext(userId)
        logger.info { "📋 SessionManager: Resetting user $userId from '$previousContext' to idle context" }
        updateSession(userId) { session ->
            session.copy(
                context = IdleCommandContext,
                pendingJobSearch = null,
                retryCount = 0,
                selectedAlertId = null,
                previousContext = session.context
            )
        }
        logger.info { "📋 SessionManager: User $userId successfully reset to idle context" }
    }
    
    override fun isInContext(userId: Long, contextType: Class<out CommandContext>): Boolean {
        val session = userSessions[userId] ?: return false
        return contextType.isInstance(session.context)
    }
    
    override fun getCurrentContext(userId: Long): CommandContext {
        return userSessions[userId]?.context ?: IdleCommandContext
    }
    
    // Debugging method to get session info
    fun getSessionInfo(userId: Long): String {
        val session = userSessions[userId] ?: return "No session found"
        return buildString {
            appendLine("User: $userId")
            appendLine("Context: ${session.context}")
            appendLine("Selected Alert ID: ${session.selectedAlertId}")
            appendLine("Pending Job Search: ${session.pendingJobSearch?.jobTitle ?: "None"}")
            appendLine("Retry Count: ${session.retryCount}")
            appendLine("Previous Context: ${session.previousContext}")
        }
    }
} 