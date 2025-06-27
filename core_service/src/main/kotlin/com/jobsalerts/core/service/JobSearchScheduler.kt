package com.jobsalerts.core.service

import com.jobsalerts.core.domain.model.JobSearchOut
import com.jobsalerts.core.domain.model.SearchJobsParams
import jakarta.annotation.PostConstruct
import jakarta.annotation.PreDestroy
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit
import org.apache.logging.log4j.kotlin.Logging
import org.quartz.*
import org.quartz.impl.StdSchedulerFactory
import org.springframework.beans.factory.annotation.Value
import org.springframework.stereotype.Service
import java.util.concurrent.ConcurrentHashMap

@Service
class JobSearchScheduler(
    private val scraperClient: ScraperClient
) : Logging {
    
    private lateinit var scheduler: Scheduler
    private val activeSearches: MutableMap<String, JobSearchOut> = ConcurrentHashMap()
    private val semaphore = Semaphore(4) // Limit to 4 concurrent jobs like main_project
    
    @Value("\${callback.url}")
    private lateinit var callbackBaseUrl: String

    @PostConstruct
    fun initializeScheduler() {
        scheduler = StdSchedulerFactory.getDefaultScheduler()
        scheduler.start()
        logger.info { "Job search scheduler started" }
    }

    @PreDestroy
    fun shutdown() {
        if (::scheduler.isInitialized && !scheduler.isShutdown) {
            scheduler.shutdown(true)
            activeSearches.clear()
            logger.info { "Job search scheduler stopped" }
        }
    }

    suspend fun addInitialJobSearches(jobSearches: List<JobSearchOut>) {
        try {
            jobSearches.forEach { search ->
                addJobSearch(search)
            }
            logger.info { "Added ${jobSearches.size} initial job searches" }
        } catch (e: Exception) {
            logger.error(e) { "Error adding initial job searches" }
        }
    }

    suspend fun addJobSearch(jobSearch: JobSearchOut) {
        try {
            // Only add if not already present
            if (jobSearch.id !in activeSearches) {
                activeSearches[jobSearch.id] = jobSearch
                scheduleJobSearch(jobSearch)
                logger.info { "Added job search: ${jobSearch.id}" }
            } else {
                logger.info { "Job search already exists: ${jobSearch.id}" }
            }
        } catch (e: Exception) {
            logger.error(e) { "Error adding job search" }
        }
    }

    suspend fun removeJobSearch(searchId: String) {
        try {
            if (searchId in activeSearches) {
                // Remove from scheduler
                val jobKey = JobKey.jobKey("job-search-$searchId", "job-searches")
                scheduler.deleteJob(jobKey)
                
                // Remove from active searches
                activeSearches.remove(searchId)
                
                logger.info { "Removed job search: $searchId" }
            } else {
                logger.warn { "Job search not found: $searchId" }
            }
        } catch (e: Exception) {
            logger.error(e) { "Error removing job search: $searchId" }
        }
    }

    suspend fun scheduleJobSearch(jobSearch: JobSearchOut) {
        try {
            val jobDataMap = JobDataMap().apply {
                put("searchId", jobSearch.id)
                put("scheduler", this@JobSearchScheduler)
            }

            val jobDetail = JobBuilder.newJob(JobSearchJob::class.java)
                .withIdentity("job-search-${jobSearch.id}", "job-searches")
                .setJobData(jobDataMap)
                .build()

            val trigger = TriggerBuilder.newTrigger()
                .withIdentity("trigger-${jobSearch.id}", "job-searches")
                .withSchedule(CronScheduleBuilder.cronSchedule(jobSearch.timePeriod.cronExpression))
                .build()

            scheduler.scheduleJob(jobDetail, trigger)
            logger.info { "Scheduled job search: ${jobSearch.toLogString()}" }

        } catch (e: Exception) {
            logger.error(e) { "Failed to schedule job search: ${jobSearch.toLogString()}" }
            throw e
        }
    }

    suspend fun unscheduleJobSearch(searchId: String) {
        try {
            val jobKey = JobKey.jobKey("job-search-$searchId", "job-searches")
            scheduler.deleteJob(jobKey)
            logger.info { "Unscheduled job search: $searchId" }
        } catch (e: Exception) {
            logger.error(e) { "Failed to unschedule job search: $searchId" }
            throw e
        }
    }

    suspend fun triggerScraperJobAndLog(jobSearch: JobSearchOut) {
        // Log all job search parameters like main_project
        val logData = mapOf(
            "job_search_id" to jobSearch.id,
            "user_id" to jobSearch.userId,
            "keywords" to jobSearch.jobTitle,
            "location" to jobSearch.location,
            "job_types" to jobSearch.jobTypes.map { it.label },
            "remote_types" to jobSearch.remoteTypes.map { it.label },
            "time_period" to jobSearch.timePeriod.displayName
        )
        
        logger.info { "Requesting scraper job: $logData" }
        
        // Build callback URL
        val callbackUrl = callbackBaseUrl.trimEnd('/') + "/api/job-results-callback"
        
        val params = SearchJobsParams(
            keywords = jobSearch.jobTitle,
            location = jobSearch.location,
            jobTypes = jobSearch.jobTypes.map { it.label },
            remoteTypes = jobSearch.remoteTypes.map { it.label },
            timePeriod = jobSearch.timePeriod.displayName,
            filterText = jobSearch.filterText,
            callbackUrl = callbackUrl,
            jobSearchId = jobSearch.id,
            userId = jobSearch.userId
        )
        
        try {
            val response = scraperClient.searchJobs(params)
            val logDataWithStatus = logData + ("callback_url" to callbackUrl) + ("status_code" to response.statusCode)
            
            if (response.isSuccessful) {
                logger.info { "Successfully triggered scraper job: $logDataWithStatus" }
            } else {
                val logDataWithResponse = logDataWithStatus + ("response_text" to response.body)
                logger.error { "Failed to trigger scraper job: $logDataWithResponse" }
            }
        } catch (e: Exception) {
            logger.error(e) { "Exception triggering scraper job: $logData" }
        }
    }

    fun getActiveSearchesCount(): Int = activeSearches.size
    
    fun getActiveSearches(): Map<String, JobSearchOut> = activeSearches.toMap()

    class JobSearchJob : Job, Logging {
        override fun execute(context: JobExecutionContext) {
            try {
                val searchId = context.jobDetail.jobDataMap.getString("searchId")
                val scheduler = context.jobDetail.jobDataMap.get("scheduler") as JobSearchScheduler
                
                logger.info { "Executing scheduled job search: $searchId" }
                
                // Execute in coroutine scope with semaphore like main_project
                runBlocking {
                    scheduler.semaphore.withPermit {
                        val jobSearch = scheduler.activeSearches[searchId]
                        if (jobSearch != null) {
                            scheduler.triggerScraperJobAndLog(jobSearch)
                        } else {
                            logger.warn { "Job search not found in active searches: $searchId" }
                        }
                    }
                }
                
                logger.info { "Completed scheduled job search: $searchId" }
            } catch (e: Exception) {
                logger.error(e) { "Error executing scheduled job search" }
            }
        }
    }
} 