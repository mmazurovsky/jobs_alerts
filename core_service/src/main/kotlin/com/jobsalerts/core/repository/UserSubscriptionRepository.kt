package com.jobsalerts.core.repository

import com.jobsalerts.core.domain.model.UserSubscription
import kotlinx.coroutines.flow.Flow
import org.springframework.data.mongodb.repository.Query
import org.springframework.data.repository.kotlin.CoroutineCrudRepository
import org.springframework.stereotype.Repository
import java.time.Instant

@Repository
interface UserSubscriptionRepository : CoroutineCrudRepository<UserSubscription, String> {
    
    /**
     * Find the currently active subscription for a user.
     * A subscription is active if:
     * 1. Not cancelled
     * 2. Current time is after activeFrom
     * 3. Current time is before activeTo
     */
    @Query("{ 'userId': ?0, 'activeFrom': { \$lte: ?1 }, 'activeTo': { \$gt: ?1 }, 'isCancelled': false }")
    suspend fun findActiveSubscription(userId: String, at: Instant = Instant.now()): UserSubscription?
    
    /**
     * Find all subscriptions for a user (active and inactive).
     */
    @Query("{ 'userId': ?0 }")
    suspend fun findAllByUserId(userId: String): Flow<UserSubscription>
    
    /**
     * Find all active (non-cancelled) subscriptions for a user.
     * This should typically return at most one subscription due to business rules.
     */
    @Query("{ 'userId': ?0, 'isCancelled': false }")
    suspend fun findActiveSubscriptionsByUserId(userId: String): Flow<UserSubscription>
    
    /**
     * Find subscriptions expiring within a certain timeframe for notifications.
     */
    @Query("{ 'activeTo': { \$gte: ?0, \$lte: ?1 }, 'isCancelled': false }")
    suspend fun findSubscriptionsExpiringBetween(from: Instant, to: Instant): Flow<UserSubscription>
}