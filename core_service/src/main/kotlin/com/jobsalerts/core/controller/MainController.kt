package com.jobsalerts.core.controller

import com.jobsalerts.core.Messages
import com.jobsalerts.core.domain.model.*
import com.jobsalerts.core.repository.JobSearchRepository
import com.jobsalerts.core.repository.SentJobRepository
import com.jobsalerts.core.service.JobSearchService
import jakarta.validation.Valid
import org.apache.logging.log4j.kotlin.Logging
import com.jobsalerts.core.infrastructure.ToTelegramEventBus
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/api")
class MainController(
    private val jobSearchService: JobSearchService,
    private val jobSearchRepository: JobSearchRepository,
    private val sentJobRepository: SentJobRepository,
    private val toTelegramEventBus: ToTelegramEventBus
) : Logging {

    @PostMapping("/job-results-callback")
    fun receiveJobResults(@Valid @RequestBody request: JobResultsCallbackRequest): ResponseEntity<JobResultsCallbackResponse> {
        logger.info { "Received job results for jobSearchId=${request.jobSearchId}, userId=${request.userId}, jobCount=${request.jobs.size}" }
        
        try {
            if (request.jobSearchId.startsWith("temp-")) {
                logger.info { "Processing job results for temp job searchId=${request.jobSearchId}" }
            } else {
                val jobSearch = jobSearchRepository.findById(request.jobSearchId)
                if (jobSearch.isEmpty) {
                    logger.warn { "Job search not found: ${request.jobSearchId}" }
                    return ResponseEntity.badRequest().body(
                        JobResultsCallbackResponse(
                            status = "error",
                            message = "Job search not found",
                            receivedCount = 0
                        )
                    )
                }
            }

            if (request.jobs.isEmpty()) {
                logger.info { "No jobs received for jobSearchId=${request.jobSearchId}" }
                return ResponseEntity.ok(JobResultsCallbackResponse(status = "received"))
            }
            
            // Filter out already sent jobs
            val sentJobs = sentJobRepository.findByUserId(request.userId)
            val sentJobUrls = sentJobs.map { it.jobUrl }.toSet()
            val newJobs = request.jobs.filter { it.link !in sentJobUrls }
            
            logger.info { "Found ${newJobs.size} new jobs for jobSearchId=${request.jobSearchId}, userId=${request.userId}" }
            
            if (newJobs.isNotEmpty()) {
                // Send notification about new jobs found
                val message = Messages.getJobNotificationMessage(newJobs, request.jobSearchId)
                
                val sendMessageEvent = ToTelegramSendMessageEvent(
                    message = message,
                    chatId = request.userId.toLong(),
                    eventSource = "job_results"
                )
                toTelegramEventBus.publish(sendMessageEvent)
                
                // Save sent jobs to prevent duplicates
                val sentJobEntities = newJobs.map { job ->
                    SentJobOut(
                        userId = request.userId,
                        jobUrl = job.link
                    )
                }
                sentJobRepository.saveAll(sentJobEntities)
                
                logger.info { "Saved ${sentJobEntities.size} sent job records and sent notification" }
            }
            
            return ResponseEntity.ok(
                JobResultsCallbackResponse(
                    status = "received",
                    message = "Jobs processed successfully",
                    receivedCount = newJobs.size
                )
            )
            
        } catch (e: Exception) {
            logger.error(e) { "Error processing job results for jobSearchId=${request.jobSearchId}" }
            
            return ResponseEntity.internalServerError().body(
                JobResultsCallbackResponse(
                    status = "error",
                    message = "Internal server error",
                    receivedCount = 0
                )
            )
        }
    }
} 