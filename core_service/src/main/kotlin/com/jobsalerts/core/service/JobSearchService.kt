package com.jobsalerts.core.service

import com.jobsalerts.core.domain.model.*
import com.jobsalerts.core.repository.JobSearchRepository
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.stereotype.Service

@Service
class JobSearchService(
    private val jobSearchRepository: JobSearchRepository,
    private val jobSearchScheduler: JobSearchScheduler,
    private val scraperJobService: ScraperJobService
) : Logging {
    

    
    fun getUserSearches(userId: Long): List<JobSearchOut> {
        return jobSearchRepository.findByUserId(userId)
    }
    
    fun getSearchById(searchId: String): JobSearchOut? {
        return jobSearchRepository.findById(searchId).orElse(null)
    }
    
    suspend fun deleteJobSearch(userId: Long, searchId: String): Boolean {
        val search = jobSearchRepository.findByIdAndUserId(searchId, userId)
        if (search != null) {
            jobSearchRepository.deleteById(searchId)
            jobSearchScheduler.removeJobSearch(searchId)
            logger.info { "Deleted job search: $searchId for user: $userId" }
            return true
        }
        return false
    }
    
    suspend fun processJobResults(searchId: String, jobs: List<JobListing>) {
        try {
            logger.info { "Processing ${jobs.size} job results for search $searchId" }
            
            // Here you would typically:
            // 1. Filter out jobs already sent to users
            // 2. Apply any additional filtering logic
            // 3. Send notifications to subscribed users
            // 4. Store sent job records
            
            // For now, just log the results
            jobs.forEach { job ->
                logger.debug { "Job: ${job.title} at ${job.company} - ${job.location}" }
            }
            
        } catch (e: Exception) {
            logger.error(e) { "Error processing job results for search $searchId" }
            throw e
        }
    }
    
    suspend fun initialize() {
        // Load all existing job searches and add them to the scheduler
        val allSearches = jobSearchRepository.findAll()
        logger.info { "Loading ${allSearches.size} existing job searches" }
        
        // Use new bulk method
        jobSearchScheduler.addInitialJobSearches(allSearches)
    }
} 