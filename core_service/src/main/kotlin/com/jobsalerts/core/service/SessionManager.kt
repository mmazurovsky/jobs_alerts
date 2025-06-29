package com.jobsalerts.core.service

import com.jobsalerts.core.domain.model.*
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.stereotype.Service
import java.util.concurrent.ConcurrentHashMap

interface UserSessionManager {
    fun getSession(userId: Long, chatId: Long, username: String?): UserSession
    fun updateSession(userId: Long, update: (UserSession) -> UserSession)
    fun setContext(userId: Long, context: CommandContext)
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
    
    override fun setContext(userId: Long, context: CommandContext) {
        logger.debug { "Setting context for user $userId to: $context" }
        updateSession(userId) { session ->
            session.copy(
                previousContext = session.context,
                context = context
            )
        }
    }
        
    override fun resetToIdle(userId: Long) {
        logger.debug { "Resetting user $userId to idle context" }
        updateSession(userId) { session ->
            session.copy(
                context = IdleCommandContext,
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