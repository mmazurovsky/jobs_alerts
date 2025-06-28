package com.jobsalerts.core.service

import com.jobsalerts.core.domain.model.*
import com.jobsalerts.core.repository.JobSearchRepository
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.stereotype.Service

@Service  
class AlertCreationService(
    private val jobSearchParserService: JobSearchParserService,
    private val jobSearchRepository: JobSearchRepository,
    private val jobSearchScheduler: JobSearchScheduler
) : Logging {

    suspend fun startAlertCreation(
        messageSender: MessageSender,
        sessionManager: UserSessionManager,
        userId: Long,
        chatId: Long,
        initialDescription: String? = null
    ) {
        if (!initialDescription.isNullOrBlank()) {
            // User provided initial description, try to parse it
            processAlertDescription(messageSender, sessionManager, userId, chatId, initialDescription)
        } else {
            // Start the conversation flow
            sessionManager.updateSession(userId) { session ->
                session.copy(
                    state = ConversationState.WaitingForAlertDescription,
                    retryCount = 0,
                    pendingJobSearch = null
                )
            }
            
            val instructionsMessage = buildString {
                appendLine("🔔 **Creating a new job alert**")
                appendLine()
                append(JobSearchIn.getFormattingInstructions())
                appendLine()
                appendLine("💡 **Note:** This will create a recurring alert that searches for jobs automatically!")
            }
            messageSender.sendMessage(chatId, instructionsMessage)
        }
    }

    suspend fun processAlertDescription(
        messageSender: MessageSender,
        sessionManager: UserSessionManager,
        userId: Long,
        chatId: Long,
        description: String
    ) {
        try {
            messageSender.sendMessage(chatId, "🔍 Analyzing your job alert description...")
            
            val parseResult = jobSearchParserService.parseUserInput(description, userId.toInt())
            
            if (parseResult.success && parseResult.jobSearchIn != null) {
                // Successfully parsed, show for confirmation
                val confirmationMessage = buildString {
                    appendLine("✅ **Job alert parsed successfully!**")
                    appendLine()
                    append(parseResult.jobSearchIn.toHumanReadableString())
                    appendLine()
                    appendLine("⏰ **Alert Frequency:** ${parseResult.jobSearchIn.timePeriod.displayName}")
                    appendLine()
                    appendLine("**Is this correct?**")
                    appendLine("• Reply '**yes**' to create the alert")
                    appendLine("• Reply '**no**' to modify your alert")
                    appendLine("• Use /cancel to abort")
                }
                
                sessionManager.updateSession(userId) { session ->
                    session.copy(
                        state = ConversationState.WaitingForAlertConfirmation,
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
            logger.error(e) { "Error processing alert description for user $userId" }
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
            messageSender.sendMessage(chatId, "❌ No pending job alert found. Please start over with /create_alert")
            resetSession(sessionManager, userId)
            return
        }

        val lowerConfirmation = confirmation.lowercase().trim()
        
        when {
            lowerConfirmation in listOf("yes", "y", "confirm", "ok", "proceed") -> {
                try {
                    messageSender.sendMessage(chatId, "🔔 **Creating your job alert...**")
                    
                    val alertId = createJobAlert(jobSearch)
                    
                    val successMessage = buildString {
                        appendLine("✅ **Job alert created successfully!**")
                        appendLine()
                        appendLine("📋 **Alert ID:** $alertId")
                        appendLine("🔍 **Searching for:** ${jobSearch.jobTitle}")
                        appendLine("📍 **Location:** ${jobSearch.location}")
                        appendLine("⏰ **Frequency:** ${jobSearch.timePeriod.displayName}")
                        appendLine()
                        appendLine("🔔 You'll receive notifications when new jobs matching your criteria are found.")
                        appendLine()
                        appendLine("Use /list_alerts to see all your alerts or /menu for other options.")
                    }
                    
                    messageSender.sendMessage(chatId, successMessage)
                    resetSession(sessionManager, userId)
                    
                } catch (e: Exception) {
                    logger.error(e) { "Error creating job alert for user $userId" }
                    messageSender.sendMessage(chatId, "❌ Failed to create job alert. Please try again later or contact support.")
                    resetSession(sessionManager, userId)
                }
            }
            
            lowerConfirmation in listOf("no", "n", "cancel", "modify", "change") -> {
                val retryMessage = buildString {
                    appendLine("📝 **Let's modify your job alert.**")
                    appendLine()
                    append(JobSearchIn.getFormattingInstructions())
                }
                
                sessionManager.updateSession(userId) { session ->
                    session.copy(
                        state = ConversationState.WaitingForAlertDescription,
                        pendingJobSearch = null,
                        retryCount = session.retryCount + 1
                    )
                }
                
                messageSender.sendMessage(chatId, retryMessage)
            }
            
            else -> {
                messageSender.sendMessage(chatId, "Please respond with '**yes**' to create the alert, '**no**' to modify, or /cancel to abort.")
            }
        }
    }

    private suspend fun createJobAlert(input: JobSearchIn): String {
        val jobSearch = JobSearchOut.fromJobSearchIn(input)
        
        val saved = jobSearchRepository.save(jobSearch)
        logger.info { "Created job search: ${saved.toLogString()}" }
        
        // Add to scheduler using new method
        jobSearchScheduler.addJobSearch(saved)
        
        return saved.id
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
                appendLine("❌ **I'm having trouble understanding your job alert description.**")
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
                appendLine("• \"Senior Software Engineer in San Francisco, full-time, remote, \$150k+, no on-call\"")
                appendLine("• \"Data Scientist role in Berlin, contract work, English speaking, avoid startups\"")
                appendLine("• \"Product Manager in New York, full-time, on-site, health insurance required\"")
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