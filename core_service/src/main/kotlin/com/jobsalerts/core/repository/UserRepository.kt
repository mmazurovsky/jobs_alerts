package com.jobsalerts.core.repository

import com.jobsalerts.core.domain.model.User
import kotlinx.coroutines.flow.Flow
import org.springframework.data.mongodb.repository.Query
import org.springframework.data.repository.kotlin.CoroutineCrudRepository
import org.springframework.stereotype.Repository

@Repository
interface UserRepository : CoroutineCrudRepository<User, String> {
    
    @Query("{ 'telegramUserId': ?0 }")
    suspend fun findByTelegramUserId(telegramUserId: Long): User?
    
    @Query("{ 'username': ?0 }")
    suspend fun findByUsername(username: String): Flow<User>
    
    @Query("{ 'lastActiveAt': { \$gte: ?0 } }")
    suspend fun findActiveUsersSince(since: java.time.Instant): Flow<User>
}