package com.jobsalerts.core.service

import com.jobsalerts.core.config.CallbackConfig
import com.jobsalerts.core.domain.model.JobSearchOut
import com.jobsalerts.core.domain.model.SearchJobsParams
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.stereotype.Service

@Service
class ScraperJobService(
        private val scraperClient: ScraperClient,
        private val callbackConfig: CallbackConfig
) : Logging {

    private val semaphore = Semaphore(4) // Limit to 4 concurrent jobs like main_project

    suspend fun triggerScraperJobAndLog(jobSearch: JobSearchOut) {
        semaphore.withPermit {
            // Build callback URL
            val callbackUrl = callbackConfig.url.trimEnd('/') + "/api/job-results-callback"

            val params =
                    SearchJobsParams(
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
                val response = scraperClient.scrapeJobs(params)
                val logDataWithStatus =
                        jobSearch.toLogString() +
                                ("callback_url" to callbackUrl) +
                                ("status_code" to response.statusCode)

                if (!response.isSuccessful) {
                    val logDataWithResponse = logDataWithStatus + ("response_text" to response.body)
                    logger.error { "Failed to trigger scraper job: $logDataWithResponse" }
                }
            } catch (e: Exception) {
                logger.error(e) { "Exception triggering scraper job: ${jobSearch.toLogString()}" }
            }
        }
    }
}
