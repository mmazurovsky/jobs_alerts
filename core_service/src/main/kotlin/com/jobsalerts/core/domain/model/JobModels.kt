package com.jobsalerts.core.domain.model

import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import org.springframework.data.annotation.Id
import org.springframework.data.mongodb.core.index.Indexed
import org.springframework.data.mongodb.core.mapping.Document

data class JobListing(
        val title: String,
        val company: String,
        val location: String,
        val description: String,
        val link: String,
        val url: String = link,
        val salary: String? = null,
        val jobType: String,
        val timestamp: String
)

data class ShortJobListing(
        val title: String,
        val company: String,
        val location: String,
        val link: String,
        val createdAgo: String,
        val description: String = ""
)

data class JobSearchIn(
        val jobTitle: String,
        val location: String,
        val jobTypes: List<JobType>,
        val remoteTypes: List<RemoteType>,
        val timePeriod: TimePeriod,
        val userId: Int,
        val filterText: String? = null
)

@Document(collection = "job_searches")
data class JobSearchOut(
        @Id val id: String,
        val jobTitle: String,
        val location: String,
        val jobTypes: List<JobType> = emptyList(),
        val remoteTypes: List<RemoteType> = emptyList(),
        val timePeriod: TimePeriod,
        val userId: Int,
        val createdAt: Instant = Instant.now(),
        val filterText: String? = null
) {
    fun toLogString(): String {
        return "id=$id, title=$jobTitle, location=$location, " +
                "job_types=${jobTypes.map { it.label }}, " +
                "remote_types=${remoteTypes.map { it.label }}, " +
                "time_period=${timePeriod.displayName}"
    }

    fun toMessage(): String {
        val humanReadableTime =
                createdAt
                        .atZone(ZoneId.systemDefault())
                        .format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"))
        return buildString {
            appendLine("🆔 Alert ID: ${id}\n")
            appendLine("Job Title: $jobTitle\n")
            appendLine("Location: $location\n")
            appendLine("Job Types: ${jobTypes.joinToString(", ")}\n")
            appendLine("Remote Types: ${remoteTypes.joinToString(", ")}\n")
            appendLine("Filter Text: $filterText\n")
            appendLine("Frequency: ${timePeriod.displayName}\n")
            appendLine("Created At: $humanReadableTime\n")
        }
    }
}

@Document(collection = "sent_jobs")
data class SentJobOut(
        @Indexed(unique = false) val userId: Long,
        @Indexed(unique = false) val jobUrl: String,
        val sentAt: Instant = Instant.now()
)

data class SearchJobsParams(
        val keywords: String,
        val location: String,
        val timePeriod: String,
        val jobTypes: List<String> = emptyList(),
        val remoteTypes: List<String> = emptyList(),
        val filterText: String? = null,
        val callbackUrl: String,
        val jobSearchId: String? = null,
        val userId: Int? = null
)

data class JobSearchRemove(val userId: Int, val searchId: String)
