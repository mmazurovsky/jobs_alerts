package com.jobsalerts.core.service

import com.jobsalerts.core.Messages
import com.jobsalerts.core.domain.model.*
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.stereotype.Service
import java.util.concurrent.ConcurrentHashMap

interface UserSessionManager {
    fun getSession(userId: Long, chatId: Long, username: String?): UserSession
    fun updateSession(userId: Long, update: (UserSession) -> UserSession): UserSession?
    fun setContext(chatId: Long, userId: Long, context: CommandContext)
    fun resetToIdle(userId: Long)
    fun isInContext(userId: Long, contextType: Class<out CommandContext>): Boolean
    fun getCurrentContext(userId: Long): CommandContext
    fun removeSession(userId: Long)
} 

@Service
class SessionManager : UserSessionManager, Logging {
    
    private val userSessions = ConcurrentHashMap<Long, UserSession>()
    
    override fun getSession(userId: Long, chatId: Long, username: String?): UserSession {
        return userSessions.computeIfAbsent(userId) { _ ->
            UserSession(
                userId = userId,
                chatId = chatId,
                username = username,
                context = IdleCommandContext,
                pendingJobSearch = null,
                selectedAlertId = null,
                retryCount = 0,
                createdAt = System.currentTimeMillis(),
                updatedAt = System.currentTimeMillis()
            )
        }
    }
    
    override fun updateSession(userId: Long, updateFunction: (UserSession) -> UserSession): UserSession? {
        return userSessions.computeIfPresent(userId) { _, existingSession ->
            updateFunction(existingSession).copy(updatedAt = System.currentTimeMillis())
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
                logger.info { "📋 SessionManager: Creating new session for user $userId with context '$context'" }
                UserSession(
                    userId = userId,
                    chatId = chatId,
                    username = null,
                    context = context,
                    previousContext = IdleCommandContext,
                    pendingJobSearch = null,
                    selectedAlertId = null,
                    retryCount = 0,
                    createdAt = System.currentTimeMillis(),
                    updatedAt = System.currentTimeMillis()
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
                previousContext = session.context,
                context = IdleCommandContext,
                pendingJobSearch = null,
                selectedAlertId = null,
                retryCount = 0,
                updatedAt = System.currentTimeMillis()
            )
        }
        logger.info { "📋 SessionManager: User $userId reset to idle context" }
    }
    
    override fun isInContext(userId: Long, contextType: Class<out CommandContext>): Boolean {
        val session = userSessions[userId] ?: return false
        return contextType.isInstance(session.context)
    }
    
    override fun getCurrentContext(userId: Long): CommandContext {
        return userSessions[userId]?.context ?: IdleCommandContext
    }
    
    override fun removeSession(userId: Long) {
        logger.info { "📋 SessionManager: Removing session for user $userId" }
        userSessions.remove(userId)
    }
} 