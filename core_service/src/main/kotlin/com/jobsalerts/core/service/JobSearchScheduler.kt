package com.jobsalerts.core.service

import com.jobsalerts.core.domain.model.JobSearchOut
import com.jobsalerts.core.service.ScraperJobService
import jakarta.annotation.PostConstruct
import jakarta.annotation.PreDestroy
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit
import org.apache.logging.log4j.kotlin.Logging
import org.quartz.*
import org.quartz.impl.StdSchedulerFactory
import org.springframework.stereotype.Service
import java.util.concurrent.ConcurrentHashMap

@Service
class JobSearchScheduler(
    private val scraperJobService: ScraperJobService
) : Logging {
    
    private lateinit var scheduler: Scheduler
    private val activeSearches: MutableMap<String, JobSearchOut> = ConcurrentHashMap()
    
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

    

    fun getActiveSearchesCount(): Int = activeSearches.size
    
    fun getActiveSearches(): Map<String, JobSearchOut> = activeSearches.toMap()

    class JobSearchJob : Job, Logging {
        override fun execute(context: JobExecutionContext) {
            try {
                val searchId = context.jobDetail.jobDataMap.getString("searchId")
                val scheduler = context.jobDetail.jobDataMap.get("scheduler") as JobSearchScheduler

                logger.info { "Executing scheduled job search: $searchId" }

                runBlocking {
                    val jobSearch = scheduler.activeSearches[searchId]
                    if (jobSearch != null) {
                        scheduler.scraperJobService.triggerScraperJobAndLog(jobSearch)
                    } else {
                        logger.warn { "Job search not found in active searches: $searchId" }
                    }
                }

                logger.info { "Completed scheduled job search: $searchId" }
            } catch (e: Exception) {
                logger.error(e) { "Error executing scheduled job search" }
            }
        }
    }
} 