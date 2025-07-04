package com.jobsalerts.core.repository

import com.jobsalerts.core.domain.model.SentJobOut
import org.springframework.data.mongodb.repository.MongoRepository
import org.springframework.stereotype.Repository
 
@Repository
interface SentJobRepository : MongoRepository<SentJobOut, String> {
    fun findByUserId(userId: Long): List<SentJobOut>
    fun existsByUserIdAndJobUrl(userId: Long, jobUrl: String): Boolean
} 