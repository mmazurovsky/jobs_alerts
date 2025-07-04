package com.jobsalerts.core.service

import com.jobsalerts.core.domain.model.User
import com.jobsalerts.core.repository.UserRepository
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.stereotype.Service
import java.time.Instant

@Service
class UserService(
    private val userRepository: UserRepository
) : Logging {

    /**
     * Get user by Telegram user ID, or create a new user if one doesn't exist.
     * This ensures that every Telegram user has a corresponding User entity.
     */
    suspend fun getOrCreateUser(telegramUserId: Long, username: String? = null): User {
        val existingUser = userRepository.findByTelegramUserId(telegramUserId)
        
        return if (existingUser != null) {
            // Update last active time and username if provided
            val updatedUser = existingUser.copy(
                lastActiveAt = Instant.now(),
                username = username ?: existingUser.username
            )
            userRepository.save(updatedUser)
        } else {
            // Create new user
            val newUser = User(
                id = generateUserId(telegramUserId),
                telegramUserId = telegramUserId,
                username = username,
                createdAt = Instant.now(),
                lastActiveAt = Instant.now()
            )
            userRepository.save(newUser)
            logger.info { "Created new user: ${newUser.id} for Telegram user: $telegramUserId" }
            newUser
        }
    }

    /**
     * Get user by Telegram user ID. Returns null if user doesn't exist.
     */
    suspend fun getUserByTelegramId(telegramUserId: Long): User? {
        return userRepository.findByTelegramUserId(telegramUserId)
    }

    /**
     * Update user's last active timestamp.
     */
    suspend fun updateLastActive(telegramUserId: Long) {
        val user = userRepository.findByTelegramUserId(telegramUserId)
        if (user != null) {
            userRepository.save(user.copy(lastActiveAt = Instant.now()))
        }
    }

    /**
     * Generate a unique user ID based on Telegram user ID.
     */
    private fun generateUserId(telegramUserId: Long): String {
        return "user-$telegramUserId"
    }
}