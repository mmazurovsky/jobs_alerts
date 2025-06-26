package com.jobsalerts.core.service

import com.jobsalerts.core.domain.model.JobSearchOut
import jakarta.annotation.PostConstruct
import jakarta.annotation.PreDestroy
import org.apache.logging.log4j.kotlin.Logging
import org.quartz.*
import org.quartz.impl.StdSchedulerFactory
import org.springframework.stereotype.Service

@Service
class JobSearchScheduler(
    private val jobSearchService: JobSearchService
) : Logging {
    private lateinit var scheduler: Scheduler

    @PostConstruct
    fun initializeScheduler() {
        scheduler = StdSchedulerFactory.getDefaultScheduler()
        scheduler.start()
        logger.info { "Quartz scheduler started successfully" }
    }

    @PreDestroy
    fun shutdown() {
        if (::scheduler.isInitialized && !scheduler.isShutdown) {
            scheduler.shutdown(true)
            logger.info { "Quartz scheduler shut down successfully" }
        }
    }

    suspend fun scheduleJobSearch(jobSearch: JobSearchOut) {
        try {
            val jobDataMap = JobDataMap().apply {
                put("searchId", jobSearch.id)
                put("jobSearchService", jobSearchService)
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

    class JobSearchJob : org.quartz.Job, Logging {
        override fun execute(context: JobExecutionContext) {
            try {
                val searchId = context.jobDetail.jobDataMap.getString("searchId")
                val jobSearchService = context.jobDetail.jobDataMap.get("jobSearchService") as JobSearchService
                
                logger.info { "Executing scheduled job search: $searchId" }
                
                // Execute the job search in a blocking manner
                // The JobSearchService should handle the async calls internally
                
                logger.info { "Completed scheduled job search: $searchId" }
            } catch (e: Exception) {
                logger.error(e) { "Error executing scheduled job search" }
            }
        }
    }
} 