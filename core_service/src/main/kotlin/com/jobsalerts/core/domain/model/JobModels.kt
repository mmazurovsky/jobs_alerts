package com.jobsalerts.core.domain.model

import com.fasterxml.jackson.annotation.JsonProperty
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import org.springframework.data.annotation.Id
import org.springframework.data.mongodb.core.mapping.Field
import org.springframework.data.mongodb.core.index.Indexed
import org.springframework.data.mongodb.core.mapping.Document
import java.time.OffsetDateTime

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
        val userId: Long,
        val filterText: String? = null
) {
    fun toHumanReadableString(): String {
        return com.jobsalerts.core.Messages.getJobSearchDetails(this)
    }
    
    companion object {
        fun getFormattingInstructions(): String {
            return com.jobsalerts.core.Messages.getJobSearchFormattingInstructions()
        }

        fun getExamples(): List<String> {
            return listOf(
                "Senior Software Engineer in San Francisco, full-time, remote, no startups, preferably in Google or Meta",
                "Data Scientist role in Berlin, contract work, no requirement to speak German, no travel required",
                "Product Manager in New York, full-time, on-site, avoid startups, health insurance provided",
                "DevOps Engineer, remote anywhere, \$120k+ salary, not mentioning SAP or Oracle",
                "Frontend Developer in London, part-time, React, not requiring PHP knowledge, flexible hours, visa sponsorship",
                "QA Engineer in Seattle, full-time, remote, automation experience, above \$90k, no manual testing",
            )
        }
    }
}

@Document(collection = "job_searches")
data class JobSearchOut(
    @Id val id: String,
    @field:Field("job_title") val jobTitle: String,
    val location: String,
    @field:Field("job_types") val jobTypes: List<JobType> = emptyList(),
    @field:Field("remote_types") val remoteTypes: List<RemoteType> = emptyList(),
    @field:Field("time_period") val timePeriod: TimePeriod,
    @field:Field("user_id") val userId: Long,
    @field:Field("created_at") val createdAt: OffsetDateTime,
    @field:Field("filter_text") val filterText: String? = null
) {
    fun toLogString(): String {
        return "id=$id, title=$jobTitle, location=$location, " +
                "job_types=${jobTypes.map { it.label }}, " +
                "remote_types=${remoteTypes.map { it.label }}, " +
                "time_period=${timePeriod.displayName}"
    }

    fun toMessage(): String {
        return buildString {
            appendLine("🆔 Alert ID: $id")
            appendLine("📝 Job Title: $jobTitle")
            appendLine("📍 Location: $location")
            appendLine("💼 Job Types: ${jobTypes.joinToString(", ") { it.label }}")
            appendLine("🏠 Remote Types: ${remoteTypes.joinToString(", ") { it.label }}")
            appendLine("🔍 Filter Text: ${filterText ?: "None"}")
            appendLine("⏰ Frequency: ${timePeriod.displayName}")
        }
    }
    
    companion object {
        /**
         * Creates a persistent JobSearchOut from JobSearchIn with a new UUID
         */
        fun fromJobSearchIn(input: JobSearchIn): JobSearchOut {
            return JobSearchOut(
                id = java.util.UUID.randomUUID().toString(),
                jobTitle = input.jobTitle,
                location = input.location,
                jobTypes = input.jobTypes,
                remoteTypes = input.remoteTypes,
                timePeriod = input.timePeriod,
                userId = input.userId,
                filterText = input.filterText,
                createdAt = OffsetDateTime.now(),
            )
        }
        
        /**
         * Creates a temporary JobSearchOut from JobSearchIn with a temporary ID prefix
         */
        fun fromJobSearchInAsTemp(input: JobSearchIn): JobSearchOut {
            return JobSearchOut(
                id = "temp-${java.util.UUID.randomUUID()}",
                jobTitle = input.jobTitle,
                location = input.location,
                jobTypes = input.jobTypes,
                remoteTypes = input.remoteTypes,
                timePeriod = input.timePeriod,
                userId = input.userId,
                filterText = input.filterText,
                createdAt = OffsetDateTime.now(),
            )
        }
    }
}

@Document(collection = "sent_jobs")
data class SentJobOut(
        @Indexed(unique = false) @field:Field("user_id") val userId: Long,
        @Indexed(unique = false) @field:Field("job_url") val jobUrl: String,
        @field:Field("sent_at") val sentAt: OffsetDateTime = OffsetDateTime.now(),
)

data class SearchJobsParams(
        val keywords: String,
        val location: String,
        @JsonProperty("time_period") val timePeriod: String,
        @JsonProperty("job_types") val jobTypes: List<String> = emptyList(),
        @JsonProperty("remote_types") val remoteTypes: List<String> = emptyList(),
        @JsonProperty("filter_text") val filterText: String? = null,
        @JsonProperty("callback_url") val callbackUrl: String,
        @JsonProperty("job_search_id") val jobSearchId: String? = null,
        @JsonProperty("user_id") val userId: Long? = null
)

data class JobSearchRemove(val userId: Long, val searchId: String)
