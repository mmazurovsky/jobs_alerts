package com.jobsalerts.core.domain.model

import com.fasterxml.jackson.annotation.JsonProperty
import jakarta.validation.constraints.NotBlank
import jakarta.validation.constraints.NotNull
import jakarta.validation.constraints.Positive

data class JobResultsRequest(
    @field:NotBlank(message = "Search ID is required")
    val searchId: String,
    
    @field:NotNull(message = "Jobs list is required")
    @field:Positive(message = "Number of jobs must be positive")
    val jobCount: Int,
    
    @field:NotNull(message = "Jobs list is required")
    val jobs: List<JobListing>
)

data class JobResultsCallbackRequest(
    @field:NotBlank(message = "Job search ID is required")
    @JsonProperty("job_search_id")
    val jobSearchId: String,
    
    @field:NotNull(message = "User ID is required")
    @field:Positive(message = "User ID must be positive")
    @JsonProperty("user_id")
    val userId: Int,
    
    @field:NotNull(message = "Jobs list is required")
    @JsonProperty("jobs")
    val jobs: List<FullJobListing>
)


data class FullJobListing(
    @JsonProperty("title")
    val title: String,
    @JsonProperty("company")
    val company: String,
    @JsonProperty("location")
    val location: String,
    @JsonProperty("link")
    val link: String,
    @JsonProperty("created_ago")
    val createdAgo: String,
    @JsonProperty("techstack")
    val techstack: List<String>,
    @JsonProperty("compatibility_score")
    val compatibilityScore: Int? = null,
    @JsonProperty("filter_reason")
    val filterReason: String? = null
)

data class JobResultsCallbackResponse(
    val status: String,
    val message: String? = null,
    val receivedCount: Int = 0
) 