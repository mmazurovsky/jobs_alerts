package com.jobsalerts.core.repository

import com.jobsalerts.core.domain.model.JobSearchOut
import org.springframework.data.mongodb.repository.MongoRepository
import org.springframework.stereotype.Repository

@Repository
interface JobSearchRepository : MongoRepository<JobSearchOut, String> {
    fun findByUserId(userId: Int): List<JobSearchOut>
    fun findByIdAndUserId(id: String, userId: Int): JobSearchOut?
    fun deleteByIdAndUserId(id: String, userId: Int): Long
} 