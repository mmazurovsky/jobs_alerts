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
) {
    fun toHumanReadableString(): String {
        return buildString {
            appendLine("🔍 **Job Search Details:**")
            appendLine("📍 **Job Title:** $jobTitle")
            appendLine("🌍 **Location:** $location")
            appendLine("💼 **Job Types:** ${jobTypes.joinToString(", ") { it.label }}")
            appendLine("🏠 **Remote Types:** ${remoteTypes.joinToString(", ") { it.label }}")
            appendLine("⏰ **Time Period:** ${timePeriod.displayName}")
            if (!filterText.isNullOrBlank()) {
                appendLine("🔍 **Filter Text:** $filterText")
            }
        }
    }
    
    companion object {
        fun getFormattingInstructions(): String {
            return buildString {
                appendLine("🔍 **How to describe your job search:**")
                appendLine()
                appendLine("Please provide your job search criteria in natural language. I'll help you parse the details.")
                appendLine()
                appendLine("**Required Fields:**")
                appendLine("• **Job Title** - What role are you looking for?")
                appendLine("  Examples: 'Software Engineer', 'Data Scientist', 'Product Manager', 'DevOps Engineer'")
                appendLine()
                appendLine("• **Location** - Where do you want to work?")
                appendLine("  Examples: 'New York', 'San Francisco', 'Remote', 'Berlin', 'London', 'anywhere'")
                appendLine()
                appendLine("**Optional Fields:**")
                appendLine("• **Job Types** - Employment type preferences:")
                appendLine("  - Available options: ${JobType.getAllLabels().joinToString(", ")}")
                appendLine("  - Default if not specified: ${JobType.getDefault().label}")
                appendLine()
                appendLine("• **Remote Types** - Work arrangement preferences:")
                appendLine("  - Available options: ${RemoteType.getAllLabels().joinToString(", ")}")
                appendLine("  - Default if not specified: ${RemoteType.getDefault().label}")
                appendLine()
                appendLine("• **Filter Text** - What you want or DON'T want in your job:")
                appendLine("  - **Salary requirements:** '\$100k+', 'above \$80k', 'competitive salary', 'equity'")
                appendLine("  - **Companies to include/avoid:** 'Google', 'no startups', 'Fortune 500 only', 'avoid consulting'")
                appendLine("  - **Communication language:** 'English only', 'German speaking', 'bilingual preferred'")
                appendLine("  - **Technologies to use/avoid:** 'Python required', 'no PHP', 'React', 'avoid legacy systems'")
                appendLine("  - **Job description filters:** 'no travel required', 'no on-call', 'flexible hours', 'no weekend work'")
                appendLine("  - **Experience level:** 'Senior level', '5+ years', 'no junior roles', 'leadership opportunities'")
                appendLine("  - **Benefits required:** 'health insurance', 'visa sponsorship', 'stock options', 'remote work'")
                appendLine()
                appendLine("**Examples:**")
                getExamples().forEachIndexed { index, example ->
                    appendLine("${index + 1}. \"$example\"")
                }
                appendLine()
                appendLine("💬 **Just describe what you're looking for, and I'll help you refine it!**")
            }
        }

        fun getExamples(): List<String> {
            return listOf(
                "Senior Software Engineer in San Francisco, full-time, remote, \$150k+, no on-call",
                "Data Scientist role in Berlin, contract work, English speaking, no travel required",
                "Product Manager in New York, full-time, on-site, avoid startups, health insurance required",
                "DevOps Engineer, remote anywhere, \$120k+ salary, Kubernetes required, no legacy systems",
                "Frontend Developer in London, part-time, React required, no PHP, flexible hours",
                "Backend Engineer in Toronto, full-time, hybrid, Java preferred, no weekend work",
                "Mobile Developer in Austin, contract, iOS experience, no Android, visa sponsorship",
                "QA Engineer in Seattle, full-time, remote, automation experience, above \$90k, no manual testing",
                "UI/UX Designer in Los Angeles, full-time, Fortune 500 companies only, Figma required",
                "Full Stack Developer, remote, internship, JavaScript required, learning opportunities, no unpaid"
            )
        }
    }
}

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
                filterText = input.filterText
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
                filterText = input.filterText
            )
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
