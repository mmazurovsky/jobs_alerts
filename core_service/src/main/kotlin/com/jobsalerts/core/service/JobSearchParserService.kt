package com.jobsalerts.core.service

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import com.fasterxml.jackson.module.kotlin.readValue
import com.jobsalerts.core.domain.model.*
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.stereotype.Service

data class JobSearchParseResult(
    val success: Boolean,
    val jobSearchIn: JobSearchIn? = null,
    val errorMessage: String? = null,
    val missingFields: List<String> = emptyList()
)

@Service
class JobSearchParserService(
    private val deepSeekClient: DeepSeekClient
) : Logging {

    private val objectMapper: ObjectMapper = jacksonObjectMapper()

    suspend fun parseUserInput(userInput: String, userId: Long): JobSearchParseResult {
        return try {
            if (!deepSeekClient.isAvailable()) {
                logger.warn { "DeepSeek API not available, falling back to basic parsing" }
                return parseBasicInput(userInput, userId)
            }

            val prompt = buildPrompt(userInput)
            val response = deepSeekClient.chat(DeepSeekRequest(prompt))
            
            if (response.success && response.content != null) {
                parseDeepSeekResponse(response.content, userId)
            } else {
                logger.error { "DeepSeek API failed: ${response.errorMessage}" }
                JobSearchParseResult(
                    success = false,
                    errorMessage = "Sorry, I couldn't parse your job search request. Please try again with a clearer description."
                )
            }
        } catch (e: Exception) {
            logger.error(e) { "Error parsing user input: $userInput" }
            JobSearchParseResult(
                success = false,
                errorMessage = "Sorry, I couldn't parse your job search request. Please try again with a clearer description."
            )
        }
    }

    private fun buildPrompt(userInput: String): String {
        val formattingInstructions = JobSearchIn.getFormattingInstructions()
        
        return """
            You are a job search assistant. Parse the following user input into a structured job search request.
            
            User Input: "$userInput"
            
            Context - Here's what users are told about how to format their requests:
            $formattingInstructions
            
            Based on this context, extract the information and return ONLY a valid JSON object with this exact structure:
            {
                "jobTitle": "extracted job title",
                "location": "extracted location", 
                "jobTypes": ["list of job types from: ${JobType.getAllLabels().joinToString(", ")}"],
                "remoteTypes": ["list of remote types from: ${RemoteType.getAllLabels().joinToString(", ")}"],
                "filterText": "what user wants or doesn't want: salary requirements, companies to include/avoid, communication language, technologies to use/avoid, job description filters, experience level, benefits required"
            }
            
            Rules:
            - jobTitle and location are REQUIRED
            - If jobTypes not specified, use ["${JobType.getDefault().label}"]
            - If remoteTypes not specified, use ["${RemoteType.getDefault().label}"]
            - filterText is optional, can be null
            - Use exact label values from the provided lists
            - Return ONLY the JSON object, no explanations
            
            Examples:
            Input: "Senior Software Engineer in San Francisco, full-time remote, $150k+, no on-call"
            Output: {"jobTitle": "Senior Software Engineer", "location": "San Francisco", "jobTypes": ["Full-time"], "remoteTypes": ["Remote"], "filterText": "$150k+, no on-call"}
            
            Input: "Data Scientist role in Berlin, contract work, English speaking, avoid startups"
            Output: {"jobTitle": "Data Scientist", "location": "Berlin", "jobTypes": ["Contract"], "remoteTypes": ["Remote"], "filterText": "English speaking, avoid startups"}
        """.trimIndent()
    }

    private fun parseDeepSeekResponse(response: String, userId: Long): JobSearchParseResult {
        return try {
            // Extract JSON from response (remove any markdown formatting)
            val jsonString = response.trim()
                .removePrefix("```json")
                .removePrefix("```")
                .removeSuffix("```")
                .trim()

            val parsedData = objectMapper.readValue<Map<String, Any>>(jsonString)
            
            val jobTitle = parsedData["jobTitle"] as? String
            val location = parsedData["location"] as? String
            val jobTypeLabels = parsedData["jobTypes"] as? List<*>
            val remoteTypeLabels = parsedData["remoteTypes"] as? List<*>
            val filterText = parsedData["filterText"] as? String

            // Validate required fields
            val missingFields = mutableListOf<String>()
            if (jobTitle.isNullOrBlank()) missingFields.add("Job Title")
            if (location.isNullOrBlank()) missingFields.add("Location")

            if (missingFields.isNotEmpty()) {
                return JobSearchParseResult(
                    success = false,
                    errorMessage = "Missing required information: ${missingFields.joinToString(", ")}",
                    missingFields = missingFields
                )
            }

            // Parse job types
            val jobTypes = jobTypeLabels?.mapNotNull { label ->
                JobType.fromLabel(label.toString())
            }?.takeIf { it.isNotEmpty() } ?: listOf(JobType.getDefault())

            // Parse remote types  
            val remoteTypes = remoteTypeLabels?.mapNotNull { label ->
                RemoteType.fromLabel(label.toString())
            }?.takeIf { it.isNotEmpty() } ?: listOf(RemoteType.getDefault())

            val jobSearchIn = JobSearchIn(
                jobTitle = jobTitle!!,
                location = location!!,
                jobTypes = jobTypes,
                remoteTypes = remoteTypes,
                timePeriod = TimePeriod.getOneTimeSearchPeriod(),
                userId = userId,
                filterText = if (filterText.isNullOrBlank()) null else filterText
            )

            JobSearchParseResult(success = true, jobSearchIn = jobSearchIn)

        } catch (e: Exception) {
            logger.error(e) { "Error parsing DeepSeek response: $response" }
            JobSearchParseResult(
                success = false,
                errorMessage = "I couldn't understand your job search description. Please provide clearer details about the job title and location."
            )
        }
    }

    private fun parseBasicInput(userInput: String, userId: Long): JobSearchParseResult {
        // Fallback basic parsing when DeepSeek is not available
        val words = userInput.lowercase().split("\\s+".toRegex())
        
        // Try to extract basic information
        val hasLocation = words.any { word ->
            listOf("in", "at", "from", "located", "based").any { userInput.lowercase().contains("$it $word") }
        }
        
        if (!hasLocation) {
            return JobSearchParseResult(
                success = false,
                errorMessage = "Please specify both a job title and location. For example: 'Software Engineer in San Francisco'",
                missingFields = listOf("Job Title", "Location")
            )
        }

        // This is a very basic fallback - in production, you might want more sophisticated parsing
        return JobSearchParseResult(
            success = false,
            errorMessage = "Advanced parsing is not available. Please provide your search in this format:\n" +
                    "Job Title: [your job title]\n" +
                    "Location: [your location]\n" +
                    "Job Type: [Full-time/Part-time/Contract/etc.]\n" +
                    "Remote: [Remote/On-site/Hybrid]"
        )
    }
} 