package com.jobsalerts.core.service

import com.jobsalerts.core.domain.model.*
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.stereotype.Service

@Service  
class ImmediateSearchService(
    private val jobSearchParserService: JobSearchParserService,
    private val jobSearchService: JobSearchService,
    private val scraperJobService: ScraperJobService
) : Logging {

    suspend fun startImmediateSearch(
        messageSender: MessageSender,
        sessionManager: UserSessionManager,
        userId: Long,
        chatId: Long,
        initialDescription: String? = null
    ) {
        if (!initialDescription.isNullOrBlank()) {
            // User provided initial description, try to parse it
            processJobSearchDescription(messageSender, sessionManager, userId, chatId, initialDescription)
        } else {
            // Start the conversation flow
            sessionManager.updateSession(userId) { session ->
                session.copy(
                    state = ConversationState.WaitingForJobSearchDescription,
                    retryCount = 0,
                    pendingJobSearch = null
                )
            }
            
            val instructionsMessage = JobSearchIn.getFormattingInstructions()
            messageSender.sendMessage(chatId, instructionsMessage)
        }
    }

    private suspend fun triggerImmediateSearch(input: JobSearchIn): String {
        // Create a temporary job search object without saving it to database
        val tempJobSearch = JobSearchOut.fromJobSearchInAsTemp(input)
        
        logger.info { "Triggering immediate search: ${tempJobSearch.toLogString()}" }
        
        try {
            // Trigger the scraper job without saving the search
            scraperJobService.triggerScraperJobAndLog(tempJobSearch)
            logger.info { "Successfully triggered immediate search for user ${input.userId}" }
            return tempJobSearch.id
        } catch (e: Exception) {
            logger.error(e) { "Failed to trigger immediate search: ${tempJobSearch.toLogString()}" }
            throw e
        }
    }


    suspend fun processJobSearchDescription(
        messageSender: MessageSender,
        sessionManager: UserSessionManager,
        userId: Long,
        chatId: Long,
        description: String
    ) {
        try {
            messageSender.sendMessage(chatId, "🔍 Analyzing your job search description...")
            
            val parseResult = jobSearchParserService.parseUserInput(description, userId.toInt())
            
            if (parseResult.success && parseResult.jobSearchIn != null) {
                // Successfully parsed, show for confirmation
                val confirmationMessage = buildString {
                    appendLine("✅ **Job search parsed successfully!**")
                    appendLine()
                    append(parseResult.jobSearchIn.toHumanReadableString())
                    appendLine()
                    appendLine("**Is this correct?**")
                    appendLine("• Reply '**yes**' to proceed with the search")
                    appendLine("• Reply '**no**' to modify your search")
                    appendLine("• Use /cancel to abort")
                }
                
                sessionManager.updateSession(userId) { session ->
                    session.copy(
                        state = ConversationState.WaitingForJobSearchConfirmation,
                        pendingJobSearch = parseResult.jobSearchIn,
                        retryCount = 0
                    )
                }
                
                messageSender.sendMessage(chatId, confirmationMessage)
            } else {
                // Parsing failed, ask for retry
                handleParseFailure(messageSender, sessionManager, userId, chatId, parseResult)
            }
        } catch (e: Exception) {
            logger.error(e) { "Error processing job search description for user $userId" }
            messageSender.sendMessage(chatId, "❌ An error occurred while processing your request. Please try again or use /cancel to abort.")
        }
    }

    suspend fun processConfirmation(
        messageSender: MessageSender,
        sessionManager: UserSessionManager,
        userId: Long,
        chatId: Long,
        username: String?,
        confirmation: String
    ) {
        val session = sessionManager.getSession(userId, chatId, username)
        val jobSearch = session.pendingJobSearch
        
        if (jobSearch == null) {
            messageSender.sendMessage(chatId, "❌ No pending job search found. Please start over with /search_now")
            resetSession(sessionManager, userId)
            return
        }

        val lowerConfirmation = confirmation.lowercase().trim()
        
        when {
            lowerConfirmation in listOf("yes", "y", "confirm", "ok", "proceed") -> {
                try {
                    messageSender.sendMessage(chatId, "🚀 **Starting your job search...**")
                    
                    val searchId = triggerImmediateSearch(jobSearch)
                    
                    val successMessage = buildString {
                        appendLine("✅ **Job search initiated successfully!**")
                        appendLine()
                        appendLine("📋 **Search ID:** $searchId")
                        appendLine("🔍 **Searching for:** ${jobSearch.jobTitle}")
                        appendLine("📍 **Location:** ${jobSearch.location}")
                        appendLine()
                        appendLine("⏳ Your job search is now running. Results will be sent to you once the search is complete in few minutes.")
                        appendLine()
                        appendLine("Use /menu to access other options.")
                    }
                    
                    messageSender.sendMessage(chatId, successMessage)
                    resetSession(sessionManager, userId)
                    
                } catch (e: Exception) {
                    logger.error(e) { "Error triggering immediate search for user $userId" }
                    messageSender.sendMessage(chatId, "❌ Failed to start job search. Please try again later or contact support.")
                    resetSession(sessionManager, userId)
                }
            }
            
            lowerConfirmation in listOf("no", "n", "cancel", "modify", "change") -> {
                val retryMessage = buildString {
                    appendLine("📝 **Let's modify your job search.**")
                    appendLine()
                    append(JobSearchIn.getFormattingInstructions())
                }
                
                sessionManager.updateSession(userId) { session ->
                    session.copy(
                        state = ConversationState.WaitingForJobSearchDescription,
                        pendingJobSearch = null,
                        retryCount = session.retryCount + 1
                    )
                }
                
                messageSender.sendMessage(chatId, retryMessage)
            }
            
            else -> {
                messageSender.sendMessage(chatId, "Please respond with '**yes**' to proceed, '**no**' to modify, or /cancel to abort.")
            }
        }
    }

    private suspend fun handleParseFailure(
        messageSender: MessageSender,
        sessionManager: UserSessionManager,
        userId: Long,
        chatId: Long,
        parseResult: JobSearchParseResult
    ) {
        val session = sessionManager.getSession(userId, chatId, "")
        val newRetryCount = session.retryCount + 1
        
        if (newRetryCount >= 3) {
            val fallbackMessage = buildString {
                appendLine("❌ **I'm having trouble understanding your job search description.**")
                appendLine()
                appendLine("Let's try a structured approach. Please provide:")
                appendLine()
                appendLine("**Job Title:** [What position are you looking for?]")
                appendLine("**Location:** [Where do you want to work?]")
                appendLine("**Job Type:** [Full-time, Part-time, Contract, etc.]")
                appendLine("**Remote Type:** [Remote, On-site, Hybrid]")
                appendLine("**Additional Requirements:** [Any other requirements or keywords]")
                appendLine()
                appendLine("Use /cancel if you want to stop.")
            }
            
            sessionManager.updateSession(userId) { session ->
                session.copy(retryCount = newRetryCount)
            }
            
            messageSender.sendMessage(chatId, fallbackMessage)
        } else {
            val errorMessage = buildString {
                appendLine("❌ **${parseResult.errorMessage}**")
                appendLine()
                if (parseResult.missingFields.isNotEmpty()) {
                    appendLine("**Missing information:** ${parseResult.missingFields.joinToString(", ")}")
                    appendLine()
                }
                appendLine("Please try again with a clearer description:")
                appendLine()
                appendLine("**Examples:**")
                appendLine("• \"Senior Software Engineer in San Francisco, full-time, remote\"")
                appendLine("• \"Data Scientist role in Berlin, contract work preferred\"")
                appendLine("• \"Product Manager in New York, full-time, on-site only\"")
                appendLine()
                appendLine("Or use /cancel to stop.")
            }
            
            sessionManager.updateSession(userId) { session ->
                session.copy(retryCount = newRetryCount)
            }
            
            messageSender.sendMessage(chatId, errorMessage)
        }
    }

    private fun resetSession(sessionManager: UserSessionManager, userId: Long) {
        sessionManager.updateSession(userId) { session ->
            session.copy(
                state = ConversationState.Idle,
                pendingJobSearch = null,
                retryCount = 0
            )
        }
    }
} 