package com.jobsalerts.core.repository

import com.jobsalerts.core.domain.model.UserUsage
import kotlinx.coroutines.flow.Flow
import org.springframework.data.mongodb.repository.Query
import org.springframework.data.mongodb.repository.Update
import org.springframework.data.repository.kotlin.CoroutineCrudRepository
import org.springframework.stereotype.Repository
import java.time.LocalDate

@Repository
interface UserUsageRepository : CoroutineCrudRepository<UserUsage, String> {
    
    /**
     * Find usage record for a specific user on a specific date.
     */
    @Query("{ 'userId': ?0, 'date': ?1 }")
    suspend fun findByUserIdAndDate(userId: String, date: String): UserUsage?
    
    /**
     * Find all usage records for a user.
     */
    @Query("{ 'userId': ?0 }")
    suspend fun findAllByUserId(userId: String): Flow<UserUsage>
    
    /**
     * Find usage records for a user within a date range.
     */
    @Query("{ 'userId': ?0, 'date': { \$gte: ?1, \$lte: ?2 } }")
    suspend fun findByUserIdAndDateRange(userId: String, fromDate: String, toDate: String): Flow<UserUsage>
    
    /**
     * Increment the instant searches count for a user on a specific date.
     * If no record exists, create one with count = 1.
     */
    suspend fun incrementDailySearches(userId: String, date: LocalDate) {
        val dateStr = date.toString() // YYYY-MM-DD format
        val existing = findByUserIdAndDate(userId, dateStr)
        
        if (existing != null) {
            save(existing.copy(instantSearchesCount = existing.instantSearchesCount + 1))
        } else {
            save(UserUsage(
                id = "$userId-$dateStr",
                userId = userId,
                date = dateStr,
                instantSearchesCount = 1,
                createdAt = java.time.Instant.now()
            ))
        }
    }
}