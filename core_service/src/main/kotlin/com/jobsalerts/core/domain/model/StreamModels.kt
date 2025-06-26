package com.jobsalerts.core.domain.model

import org.springframework.context.ApplicationEvent

// Base event for all job alerts events
abstract class JobAlertsEvent(
    val eventData: Any,
    open val eventSource: String
) : ApplicationEvent(eventSource)

// Message events for Telegram bot communication
data class SendMessageEvent(
    val message: String,
    val chatId: Long?,
    override val eventSource: String
) : JobAlertsEvent(message, eventSource)

// // Job-related events
// sealed class JobEvent(
//     eventData: Any,
//     eventSource: String
// ) : JobAlertsEvent(eventSource, eventData ) {
    
//     data class JobFound(
//         val source: Any,
//         val job: JobListing,
//         val searchId: String
//     ) : JobEvent(source, job, "job-search")
    
//     data class SearchCompleted(
//         val source: Any,
//         val searchId: String,
//         val jobCount: Int
//     ) : JobEvent(source, jobCount, "job-search")
    
//     data class SearchError(
//         val source: Any,
//         val searchId: String,
//         val error: String,
//         val exception: Throwable? = null
//     ) : JobEvent(source, error, "job-search")
    
//     data class JobsReceived(
//         val source: Any,
//         val jobs: List<FullJobListing>,
//         val searchId: String,
//         val userId: String
//     ) : JobEvent(source, jobs, "callback")
// } 