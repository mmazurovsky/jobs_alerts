package com.jobsalerts.core

import com.jobsalerts.core.domain.model.*
import com.jobsalerts.core.service.JobSearchParseResult

/**
 * Centralized class for all application messages and string templates.
 * Contains static constants and dynamic methods for generating user-facing text.
 */
object Messages {

    // ================== STATIC CONSTANTS ==================

    // === Commands ===
    const val CMD_CANCEL = "/cancel"
    const val CMD_START = "/start"
    const val CMD_MENU = "/menu"
    const val CMD_HELP = "/help"
    const val CMD_CREATE_ALERT = "/create_alert"
    const val CMD_LIST_ALERTS = "/list_alerts"
    const val CMD_EDIT_ALERT = "/edit_alert"
    const val CMD_DELETE_ALERT = "/delete_alert"
    const val CMD_SEARCH_NOW = "/search_now"

    const val CANCEL_MESSAGE = "❌ Operation cancelled."
    const val USE_CANCEL_TO_ABORT = "Use $CMD_CANCEL to abort this operation."

    // === Error Messages ===
    const val ERROR_GENERAL =
        "❌ An error occurred while processing your request. Please try again or use $CMD_CANCEL to abort."
    const val ERROR_RETRIEVAL = "❌ Error retrieving your job alerts. Please try again later."
    const val ERROR_PROCESSING = "❌ Error processing your request. Please try again later."
    const val ERROR_CREATION_FAILED =
        "❌ Failed to create job alert. Please try again later or contact support."
    const val ERROR_UPDATE_FAILED =
        "❌ Failed to update job alert. Please try again later or contact support."
    const val ERROR_DELETION_FAILED = "❌ Failed to delete alert(s). Please try again later."
    const val ERROR_NO_PENDING_ALERT =
        "❌ No pending job alert found. Please start over with $CMD_CREATE_ALERT"
    const val ERROR_NO_PENDING_SEARCH =
        "❌ No pending job search found. Please start over with $CMD_SEARCH_NOW"
    const val ERROR_DISPLAY_HELP = "❌ Error displaying help. Please try again later."
    const val ERROR_DISPLAY_WELCOME = "❌ Error displaying welcome message. Please try again later."
    const val ERROR_DISPLAY_MENU = "❌ Error displaying menu. Please try again later."

    // === Success Messages ===
    const val SUCCESS_PARSED = "✅ <b>Job search parsed successfully!</b>"
    const val SUCCESS_ALERT_PARSED = "✅ <b>Job alert parsed successfully!</b>"
    const val SUCCESS_UPDATED_PARSED = "✅ <b>Updated job search parsed successfully!</b>"

    // === Headers ===
    const val HEADER_WELCOME =
        "🤖 Welcome to Job Search Alerts Bot powered by AI for prompt-based filtering! I will help you to become the first applicant for jobs that match your specific prompt."
    const val HEADER_MAIN_MENU = "📋 <b>Main Menu</b>"
    const val HEADER_HELP = "📖 <b>Job Alerts Bot - Help</b>"
    const val HEADER_CREATE_ALERT = "🔔 <b>Creating a new job alert</b>"
    const val HEADER_IMMEDIATE_SEARCH = "🔍 <b>Running an immediate job search</b>"
    const val HEADER_DELETE_ALERT = "🗑️ <b>Delete Job Alert</b>"
    const val HEADER_EDIT_ALERT = "✏️ <b>Edit Job Alert</b>"
    const val HEADER_YOUR_ALERTS = "📋 <b>Your Active Job Alerts</b>"
    const val HEADER_DELETE_CONFIRMATION = "🗑️ <b>Delete Alert Confirmation</b>"
    const val HEADER_INVALID_ALERT_ID = "❌ <b>Invalid Alert ID</b>"
    const val HEADER_INVALID_ALERT_IDS = "❌ <b>Invalid Alert ID(s)</b>"
    const val HEADER_JOB_SEARCH_DETAILS = "🔍 <b>Job Search Details:</b>"
    const val HEADER_EDITING_ALERT = "✏️ <b>Editing Alert:</b>"
    const val HEADER_CURRENT_ALERT_DETAILS = "<b>Current Alert Details:</b>"
    const val HEADER_AVAILABLE_ACTIONS = "<b>Possible Actions:</b>"
    const val HEADER_REQUIRED_FIELDS = "<b>Required Fields:</b>"
    const val HEADER_OPTIONAL_FIELDS = "<b>Optional Fields:</b>"
    const val HEADER_EXAMPLES = "<b>Examples:</b>"
    const val HEADER_EXAMPLE_DESCRIPTIONS = "<b>Example Descriptions:</b>"

    // === Section Dividers ===
    const val DIVIDER_40 = "────────────────────────────────────────"

    // === Structured Approach Template ===
    const val STRUCTURED_APPROACH_HEADER = "Let's try a structured approach. Please provide:"
    const val STRUCTURED_JOB_TITLE = "<b>Job Title:</b> [What position are you looking for?]"
    const val STRUCTURED_LOCATION = "<b>Location:</b> [Where do you want to work?]"
    const val STRUCTURED_JOB_TYPE = "<b>Job Type:</b> [Full-time, Part-time, Contract, etc.]"
    const val STRUCTURED_REMOTE_TYPE = "<b>Remote Type:</b> [Remote, On-site, Hybrid]"
    const val STRUCTURED_REQUIREMENTS =
        "<b>Additional Requirements:</b> [Any other requirements or keywords]"

    // === Common Instructions ===
    const val INSTRUCTION_IS_CORRECT = "<b>Is this correct?</b>"
    const val INSTRUCTION_RETRY_DESCRIPTION = "Please try again with a clearer description:"
    const val INSTRUCTION_PROVIDE_VALID_ID =
        "Please provide a valid alert ID or use $CMD_LIST_ALERTS to see your alerts."
    const val INSTRUCTION_USE_LIST_ALERTS =
        "Use $CMD_LIST_ALERTS to see your alerts or $CMD_CANCEL to abort."

    // === Notes ===
    const val NOTE_RECURRING_ALERT =
        "💡 <b>Note:</b> This will create a recurring alert that searches for jobs automatically!"
    const val NOTE_ONE_TIME_SEARCH =
        "💡 <b>Note:</b> This is a one-time search that will start executing immediately!"
    const val NOTE_RESULTS_NOTIFICATION =
        "🔔 You'll receive notifications when new jobs matching your criteria are found."
    const val NOTE_CANNOT_UNDO = "⚠️ <b>Warning:</b> This action cannot be undone!"
    const val NOTE_SEARCH_RUNNING =
        "⏳ Your job search is now running. Results will be sent to you once the search is complete in few minutes."
    const val NOTE_UPDATED_ALERT_ACTIVE =
        "🔔 Your updated alert is now active and will search for jobs with the new criteria."

    // === Menu Items ===
    const val MENU_SEARCH_NOW = "$CMD_SEARCH_NOW - Search jobs immediately with AI"
    const val MENU_CREATE_ALERT = "$CMD_CREATE_ALERT - Create new job alert with AI"
    const val MENU_LIST_ALERTS = "$CMD_LIST_ALERTS - View your created alerts"
    const val MENU_EDIT_ALERT = "$CMD_EDIT_ALERT - Edit a created alert"
    const val MENU_DELETE_ALERT = "$CMD_DELETE_ALERT - Delete an alert"

    const val MENU_HELP = "$CMD_HELP - Detailed help"

    // === Loading Messages ===
    const val ANALYZING_DESCRIPTION = "Analyzing your job alert description..."
    const val ANALYZING_SEARCH = "Analyzing your job search description..."
    const val ANALYZING_UPDATE = "Analyzing your updated job search..."
    const val CREATING_ALERT = "<b>Creating your job alert...</b>"
    const val UPDATING_ALERT = "✏<b>Updating your job alert...</b>"
    const val STARTING_SEARCH = "<b>Starting your job search...</b>"

    // ================== DYNAMIC METHODS ==================

    // === Welcome and Menu Messages ===
    fun getWelcomeMessage(): String = buildString {
        appendLine(HEADER_WELCOME)
        appendLine()
        appendLine("I'll help you stay updated with the latest job opportunities matching your prompt.")
        appendLine("Use the commands below to get started:")
        appendLine()
        appendLine("$CMD_MENU - Show main menu")
        appendLine(MENU_SEARCH_NOW)
        appendLine(MENU_CREATE_ALERT)
        appendLine(MENU_LIST_ALERTS)
        appendLine(MENU_EDIT_ALERT)
        appendLine(MENU_DELETE_ALERT)
        appendLine("$CMD_HELP - Show detailed help")
        appendLine()
        appendLine("Type any command like $CMD_CREATE_ALERT or $CMD_SEARCH_NOW to get started!")
    }

    fun getMainMenuMessage(): String = buildString {
        appendLine(HEADER_MAIN_MENU)
        appendLine()
        appendLine("Choose what you'd like to do:")
        appendLine()
        appendLine("<b>🔍 Search Jobs Immediately:</b>")
        appendLine("(Search without creating recurring alert)")
        appendLine(MENU_SEARCH_NOW)
        appendLine()
        appendLine("<b>🔔 Job Alert Management:</b>")
        appendLine(MENU_CREATE_ALERT)
        appendLine(MENU_LIST_ALERTS)
        appendLine(MENU_EDIT_ALERT)
        appendLine(MENU_DELETE_ALERT)
        appendLine()
        appendLine("<b>📖 Help & Info:</b>")
        appendLine(MENU_HELP)
        appendLine()
        appendLine("Just use any command to get started!")
    }

    fun getHelpMessage(): String = buildString {
        appendLine(HEADER_HELP)
        appendLine()
        appendLine("<b>Main Commands:</b>")
        appendLine("$CMD_START - Welcome message and command overview")
        appendLine("$CMD_MENU - Show main menu with quick options")
        appendLine("$CMD_HELP - Show this help message")
        appendLine("$CMD_CANCEL - Cancel current operation")
        appendLine()
        appendLine("<b>Job Alert Management:</b>")
        appendLine("$CMD_CREATE_ALERT - Create a new job search alert")
        appendLine("$CMD_LIST_ALERTS - View all your active job alerts")
        appendLine("$CMD_EDIT_ALERT - Modify an existing job alert")
        appendLine("$CMD_DELETE_ALERT - Remove a job alert")
        appendLine()
        appendLine("<b>Job Search Format:</b>")
        appendLine("When creating or editing alerts, you can describe your job requirements in natural language:")
        appendLine("\"Looking for Senior Python Developer job in Berlin, remote only, no requirement to speak Italian, no startups\"")
        appendLine()
        appendLine("<b>Need More Help?</b>")
        appendLine("If you encounter any issues or need assistance, feel free to contact support at <a href=\"mailto:job.search.ai.bot@gmail.com\">job.search.ai.bot@gmail.com</a>")
    }

    // === Job Alert Creation Messages ===
    fun getCreateAlertInstructions(): String = buildString {
        appendLine(HEADER_CREATE_ALERT)
        appendLine()
        append(JobSearchIn.getFormattingInstructions())
        appendLine()
        appendLine(NOTE_RECURRING_ALERT)
    }

    fun getImmediateSearchInstructions(): String = buildString {
        appendLine(HEADER_IMMEDIATE_SEARCH)
        appendLine()
        append(JobSearchIn.getFormattingInstructions())
        appendLine()
        appendLine(NOTE_ONE_TIME_SEARCH)
    }

    // === Confirmation Messages ===
    fun getAlertCreationConfirmation(jobSearch: JobSearchIn): String = buildString {
        appendLine(SUCCESS_ALERT_PARSED)
        appendLine()
        append(jobSearch.toHumanReadableString())
        appendLine()
        appendLine(INSTRUCTION_IS_CORRECT)
        appendLine("• Reply '<b>yes</b>' to create the alert")
        appendLine("• Reply '<b>no</b>' to modify your alert")
        appendLine("• Use $CMD_CANCEL to abort")
    }

    fun getSearchConfirmation(jobSearch: JobSearchIn): String = buildString {
        appendLine(SUCCESS_PARSED)
        appendLine()
        append(jobSearch.toHumanReadableString())
        appendLine()
        appendLine(INSTRUCTION_IS_CORRECT)
        appendLine("• Reply '<b>yes</b>' to proceed with the search")
        appendLine("• Reply '<b>no</b>' to modify your search")
        appendLine("• Use $CMD_CANCEL to abort")
    }

    fun getEditConfirmation(alertId: String, jobSearch: JobSearchIn): String = buildString {
        appendLine(SUCCESS_UPDATED_PARSED)
        appendLine()
        appendLine("<b>Alert ID:</b> $alertId")
        appendLine()
        append(jobSearch.toHumanReadableString())
        appendLine()
        appendLine(INSTRUCTION_IS_CORRECT)
        appendLine("• Reply '<b>yes</b>' to save the changes")
        appendLine("• Reply '<b>no</b>' to modify your criteria")
        appendLine("• Use $CMD_CANCEL to abort")
    }

    // === Success Messages ===
    fun getAlertCreatedSuccess(alertId: String, jobSearch: JobSearchIn): String = buildString {
        appendLine("✅ <b>Job alert created successfully!</b>")
        appendLine()
        appendLine("\uD83C\uDD94 <b>Alert ID:</b> $alertId")
        appendLine("<b>Searching for:</b> ${jobSearch.jobTitle}")
        appendLine("<b>Location:</b> ${jobSearch.location}")
        appendLine("<b>Frequency:</b> ${jobSearch.timePeriod.displayName}")
        appendLine()
        appendLine(NOTE_RESULTS_NOTIFICATION)
        appendLine()
        appendLine("Use $CMD_LIST_ALERTS to see all your alerts or $CMD_MENU for other options.")
    }

    fun getSearchInitiatedSuccess(searchId: String, jobSearch: JobSearchIn): String = buildString {
        appendLine("✅ <b>Job search initiated successfully!</b>")
        appendLine()
        appendLine("📋 <b>Search ID:</b> $searchId")
        appendLine("🔍 <b>Searching for:</b> ${jobSearch.jobTitle}")
        appendLine("📍 <b>Location:</b> ${jobSearch.location}")
        appendLine()
        appendLine(NOTE_SEARCH_RUNNING)
        appendLine()
        appendLine("Use $CMD_MENU to access other options.")
    }

    fun getAlertUpdatedSuccess(alertId: String, jobSearch: JobSearchIn): String = buildString {
        appendLine("✅ <b>Job alert updated successfully!</b>")
        appendLine()
        appendLine("📋 <b>Alert ID:</b> $alertId")
        appendLine("🔍 <b>Searching for:</b> ${jobSearch.jobTitle}")
        appendLine("📍 <b>Location:</b> ${jobSearch.location}")
        appendLine("⏰ <b>Frequency:</b> ${jobSearch.timePeriod.displayName}")
        appendLine()
        appendLine(NOTE_UPDATED_ALERT_ACTIVE)
        appendLine()
        appendLine("Use $CMD_LIST_ALERTS to see all your alerts or $CMD_MENU for other options.")
    }

    // === Delete Alert Messages ===
    fun getNoAlertsToDeleteMessage(): String = buildString {
        appendLine(HEADER_DELETE_ALERT)
        appendLine()
        appendLine("You don't have any active job alerts to delete.")
        appendLine()
        appendLine("<b>Get started:</b>")
        appendLine("$CMD_CREATE_ALERT - Create your first job alert")
        appendLine("$CMD_HELP - See all available commands")
    }

    fun getSelectAlertToDeleteMessage(userSearches: List<JobSearchOut>): String = buildString {
        appendLine(HEADER_DELETE_ALERT)
        appendLine()
        appendLine("Which alert(s) would you like to delete? Please provide the alert ID(s).")
        appendLine()
        appendLine("<b>Your Active Job Alerts:</b>")
        appendLine()

        userSearches.forEach { jobSearch ->
            append(jobSearch.toMessage())
            appendLine(DIVIDER_40)
            appendLine()
        }

        appendLine(HEADER_EXAMPLES)
        appendLine("• <b>123</b> - Delete alert with ID 123")
        appendLine("• <b>123,456</b> - Delete alerts with IDs 123 and 456")
        appendLine()
        appendLine(USE_CANCEL_TO_ABORT)
    }

    fun getDeleteConfirmationMessage(validAlertIds: List<String>): String = buildString {
        appendLine(HEADER_DELETE_CONFIRMATION)
        appendLine()
        if (validAlertIds.size == 1) {
            appendLine("Are you sure you want to delete alert: <b>${validAlertIds[0]}</b>?")
        } else {
            appendLine("Are you sure you want to delete these ${validAlertIds.size} alerts?")
            validAlertIds.forEach { appendLine("• <b>$it</b>") }
        }
        appendLine()
        appendLine(NOTE_CANNOT_UNDO)
        appendLine()
        appendLine("• Reply '<b>yes</b>' to confirm deletion")
        appendLine("• Reply '<b>no</b>' to cancel")
        appendLine("• Use $CMD_CANCEL to abort this operation")
    }

    fun getInvalidAlertIdsMessage(
        invalidAlertIds: List<String>,
        validAlertIds: List<String>
    ): String = buildString {
        appendLine(HEADER_INVALID_ALERT_IDS)
        appendLine()
        appendLine("The following alert ID(s) don't exist or don't belong to you:")
        invalidAlertIds.forEach { appendLine("• $it") }
        appendLine()
        if (validAlertIds.isNotEmpty()) {
            appendLine("Valid alert ID(s): ${validAlertIds.joinToString(", ")}")
            appendLine()
            appendLine("Please provide only valid alert IDs or use $CMD_CANCEL to abort.")
        } else {
            appendLine("Please provide valid alert ID(s) or use $CMD_LIST_ALERTS to see your alerts.")
        }
    }

    fun getDeletionResultMessage(deletedIds: List<String>, failedIds: List<String>): String =
        buildString {
            if (deletedIds.isNotEmpty()) {
                if (deletedIds.size == 1) {
                    appendLine("✅ <b>Alert ${deletedIds[0]} has been deleted successfully.</b>")
                } else {
                    appendLine("✅ <b>${deletedIds.size} alerts have been deleted successfully:</b>")
                    deletedIds.forEach { appendLine("• $it") }
                }
            }

            if (failedIds.isNotEmpty()) {
                appendLine()
                appendLine("❌ <b>Failed to delete the following alert(s):</b>")
                failedIds.forEach { appendLine("• $it") }
                appendLine("Please try again later or contact support.")
            }
        }

    // === Edit Alert Messages ===
    fun getNoAlertsToEditMessage(): String = buildString {
        appendLine(HEADER_EDIT_ALERT)
        appendLine()
        appendLine("You don't have any active job alerts to edit.")
        appendLine()
        appendLine("<b>Get started:</b>")
        appendLine("$CMD_CREATE_ALERT - Create your first job alert")
        appendLine("$CMD_HELP - See all available commands")
    }

    fun getSelectAlertToEditMessage(userSearches: List<JobSearchOut>): String = buildString {
        appendLine(HEADER_EDIT_ALERT)
        appendLine()
        appendLine("Which alert would you like to edit? Please provide the alert ID.")
        appendLine()
        appendLine("<b>Your Active Job Alerts:</b>")
        appendLine()

        userSearches.forEach { jobSearch ->
            append(jobSearch.toMessage())
            appendLine(DIVIDER_40)
            appendLine()
        }

        appendLine("<b>Example:</b> <b>123</b> (just the ID number)")
        appendLine()
        appendLine(USE_CANCEL_TO_ABORT)
    }

    fun getInvalidAlertIdMessage(alertId: String): String = buildString {
        appendLine(HEADER_INVALID_ALERT_ID)
        appendLine()
        appendLine("Alert ID '$alertId' doesn't exist or doesn't belong to you.")
        appendLine()
        appendLine(INSTRUCTION_PROVIDE_VALID_ID)
    }

    fun getEditAlertDetailsMessage(alertId: String, existingAlert: JobSearchOut): String =
        buildString {
            appendLine("$HEADER_EDITING_ALERT $alertId</b>")
            appendLine()
            appendLine(HEADER_CURRENT_ALERT_DETAILS)
            appendLine()
            append(existingAlert.toMessage())
            appendLine(DIVIDER_40)
            appendLine()
            appendLine("Please provide the new job search criteria:")
            appendLine()
            append(JobSearchIn.getFormattingInstructions())
            appendLine()
            appendLine(USE_CANCEL_TO_ABORT)
        }

    // === List Alerts Messages ===
    fun getNoActiveAlertsMessage(): String = buildString {
        appendLine(HEADER_YOUR_ALERTS)
        appendLine()
        appendLine("You don't have any active job alerts yet.")
        appendLine()
        appendLine("<b>Get started:</b>")
        appendLine("$CMD_CREATE_ALERT - Create your first job alert")
        appendLine("$CMD_HELP - See all available commands")
        appendLine()
        appendLine("Ready to find your next opportunity? 🚀")
    }

    fun getActiveAlertsMessage(userSearches: List<JobSearchOut>): String = buildString {
        appendLine("$HEADER_YOUR_ALERTS (${userSearches.size} total)")
        appendLine()

        userSearches.forEach { jobSearch ->
            append(jobSearch.toMessage())
            appendLine(DIVIDER_40)
            appendLine()
        }

        appendLine(HEADER_AVAILABLE_ACTIONS)
        appendLine(MENU_EDIT_ALERT)
        appendLine(MENU_DELETE_ALERT)
    }

    // === Retry and Error Messages ===
    fun getRetryJobSearchMessage(): String = buildString {
        appendLine("📝 <b>Let's modify your job search.</b>")
        appendLine()
        append(JobSearchIn.getFormattingInstructions())
    }

    fun getRetryJobAlertMessage(): String = buildString {
        appendLine("📝 <b>Let's modify your job alert.</b>")
        appendLine()
        append(JobSearchIn.getFormattingInstructions())
    }

    fun getStructuredApproachMessage(): String = buildString {
        appendLine("❌ <b>I'm having trouble understanding your job search description.</b>")
        appendLine()
        appendLine(STRUCTURED_APPROACH_HEADER)
        appendLine()
        appendLine(STRUCTURED_JOB_TITLE)
        appendLine(STRUCTURED_LOCATION)
        appendLine(STRUCTURED_JOB_TYPE)
        appendLine(STRUCTURED_REMOTE_TYPE)
        appendLine(STRUCTURED_REQUIREMENTS)
        appendLine()
        appendLine("Use $CMD_CANCEL if you want to stop.")
    }

    fun getParseErrorMessage(parseResult: JobSearchParseResult): String = buildString {
        appendLine("❌ <b>${parseResult.errorMessage}</b>")
        appendLine()
        if (parseResult.missingFields.isNotEmpty()) {
            appendLine("<b>Missing information:</b> ${parseResult.missingFields.joinToString(", ")}")
            appendLine()
        }
        appendLine(INSTRUCTION_RETRY_DESCRIPTION)
        appendLine()
        appendLine(HEADER_EXAMPLES)
        appendLine("• \"Senior Software Engineer in San Francisco, full-time, remote\"")
        appendLine("• \"Data Scientist role in Berlin, contract work preferred\"")
        appendLine("• \"Product Manager in New York, full-time, on-site only\"")
        appendLine()
        appendLine("Or use $CMD_CANCEL to stop.")
    }

    fun getParseErrorMessageForAlert(parseResult: JobSearchParseResult): String = buildString {
        appendLine("❌ <b>${parseResult.errorMessage}</b>")
        appendLine()
        if (parseResult.missingFields.isNotEmpty()) {
            appendLine("<b>Missing information:</b> ${parseResult.missingFields.joinToString(", ")}")
            appendLine()
        }
        appendLine(INSTRUCTION_RETRY_DESCRIPTION)
        appendLine()
        appendLine(HEADER_EXAMPLES)
        appendLine("• \"Senior Software Engineer in San Francisco, full-time, remote, \$150k+, no on-call\"")
        appendLine("• \"Data Scientist role in Berlin, contract work, English speaking, avoid startups\"")
        appendLine("• \"Product Manager in New York, full-time, on-site, health insurance required\"")
        appendLine()
        appendLine("Or use $CMD_CANCEL to stop.")
    }

    // === Job Results Messages ===
    fun getJobResultsMessage(jobs: List<FullJobListing>): String = buildString {
        appendLine("🔔 <b>New job listings found for your search:</b>")
        appendLine()
        jobs.forEach { job ->
            appendLine(job.toMessage())
            appendLine()
        }
    }

    // === Common Confirmation Responses ===
    fun getConfirmationInstruction(actionType: String): String = when (actionType) {
        "create" -> "Please respond with '<b>yes</b>' to create the alert, '<b>no</b>' to edit description again, or $CMD_CANCEL to abort."
        "delete" -> "Please respond with '<b>yes</b>' to delete the alert(s), '<b>no</b>' to cancel, or $CMD_CANCEL to abort."
        "edit" -> "Please respond with '<b>yes</b>' to save the changes, '<b>no</b>' to modify changes again, or $CMD_CANCEL to abort."
        "search" -> "Please respond with '<b>yes</b>' to proceed, '<b>no</b>' to modify description again, or $CMD_CANCEL to abort."
        else -> "Please respond with '<b>yes</b>' to proceed, '<b>no</b>' to cancel, or $CMD_CANCEL to abort."
    }

    // === Session Debug Messages ===
    fun getSessionInfo(userId: Long, session: UserSession): String = buildString {
        appendLine("User: $userId")
        appendLine("Context: ${session.context}")
        appendLine("Selected Alert ID: ${session.selectedAlertId}")
        appendLine("Pending Job Search: ${session.pendingJobSearch?.jobTitle ?: "None"}")
        appendLine("Retry Count: ${session.retryCount}")
        appendLine("Previous Context: ${session.previousContext}")
    }

    // === Job Search Display Messages ===
    fun getJobSearchDetails(jobSearch: JobSearchIn): String = buildString {
        appendLine("🔍 <b>Job Search Details:</b>")
        appendLine("📍 <b>Job Title:</b> ${jobSearch.jobTitle}")
        appendLine("🌍 <b>Location:</b> ${jobSearch.location}")
        appendLine("💼 <b>Job Types:</b> ${jobSearch.jobTypes.joinToString(", ") { it.label }}")
        appendLine("🏠 <b>Remote Types:</b> ${jobSearch.remoteTypes.joinToString(", ") { it.label }}")
        appendLine("⏰ <b>Time Period:</b> ${jobSearch.timePeriod.displayName}")
        if (!jobSearch.filterText.isNullOrBlank()) {
            appendLine("🔍 <b>Filter Text:</b> ${jobSearch.filterText}")
        }
    }

    fun getJobSearchFormattingInstructions(): String = buildString {
        appendLine("🔍 <b>How to describe your job search:</b>")
        appendLine()
        appendLine("Please provide your job search criteria in natural language. I'll help you parse the details.")
        appendLine()
        appendLine("<b>Required Data:</b>")
        appendLine("• <b>Job Title</b> - What role are you looking for?")
        appendLine("  Examples: 'Python Software Engineer', 'Senior Data Scientist', 'Product Manager', 'DevOps Engineer'")
        appendLine()
        appendLine("• <b>Location</b> - Where do you want to work?")
        appendLine("  Examples: New York, San Francisco, Berlin, London, Vancouver, Worldwide")
        appendLine()
        appendLine("<b>Optional Data:</b>")
        appendLine("• <b>Job Types</b> - Employment type preferences:")
        appendLine("  - Available options: Full-time, Part-time, Contract, Internship")
        appendLine("  - Default if not specified: Full-time")
        appendLine()
        appendLine("• <b>Remote Types</b> - Work arrangement preferences:")
        appendLine("  - Available options: Remote, On-site, Hybrid")
        appendLine("  - Default if not specified: Any")
        appendLine()
        appendLine("• <b>Alert Frequency</b> - How often bot should search for jobs and write you a message with results:")
        appendLine("  - Recommended options: Daily, Weekly")
        appendLine("  - Default if not specified: Daily")
        appendLine()
        appendLine("• <b>Filter Text</b> - Additional prompt with specific requirements or exclusions")
        appendLine("  Examples: 'no on-call', 'without requirement to speak German', 'providing visa sponsorship', 'employer should not be a startup', 'no relocation required'")
        appendLine()
        appendLine("<b>Example Descriptions:</b>")
        appendLine("• \"Senior Software Engineer in San Francisco, full-time, remote, no startups, preferably in Google or Meta\"")
        appendLine("• \"Data Scientist role in Berlin, contract work, no requirement to speak German, no travel required\"")
        appendLine("• \"Product Manager in New York, full-time, on-site, avoid startups, health insurance provided\"")
        appendLine("• \"DevOps Engineer, remote anywhere, \$120k+ salary, not mentioning SAP or Oracle\"")
        appendLine("• \"Frontend Developer in London, part-time, React, not requiring PHP knowledge, flexible hours, visa sponsorship\"")
        appendLine("• \"QA Engineer in Seattle, full-time, remote, automation experience, above \$90k, no manual testing\"")
        appendLine()
        appendLine("Feel free to describe your requirements in natural language - I'll help parse the details!")
    }

    fun getJobListingMessage(job: FullJobListing): String = buildString {
        appendLine("⭐ <b>Compatibility:</b> ${job.compatibilityScore ?: "N/A"}")
        appendLine("📝 <b>Title:</b> ${job.title}")
        appendLine("🏢 <b>Employer:</b> ${job.company}")
        appendLine("🔧 <b>Tech Stack:</b> ${job.techstack.joinToString(", ")}")
        appendLine("📍 <b>Location:</b> ${job.location}")
        appendLine("📅 <b>Created:</b> ${job.createdAgo}")
        if (!job.filterReason.isNullOrBlank()) {
            appendLine("🤖 <b>AI Reasoning:</b> ${job.filterReason}")
        }
        appendLine("🔗 <b>Link:</b> ${job.link}")
    }

    fun getJobNotificationMessage(newJobs: List<FullJobListing>, searchId: String): String =
        buildString {
            appendLine("🎉 Found ${newJobs.size} new jobs for '$searchId'!")
            appendLine()
            newJobs.forEach { job ->
                appendLine("Compatibility: ${job.compatibilityScore ?: "N/A"}")
                appendLine("📋 ${job.title}")
                appendLine("🏢 ${job.company}")
                appendLine("📍 ${job.location}")
                appendLine("\uD83C\uDFF7\uFE0F ${job.techstack.joinToString(", ")}")
                appendLine("⌛ ${job.createdAgo}")
                appendLine("🔗 ${job.link}")
                appendLine()
            }
        }

    // === Edit Alert Messages (from EditSearchService) ===

    fun getInvalidAlertIdForEditMessage(alertId: String): String = buildString {
        appendLine("❌ <b>Invalid Alert ID</b>")
        appendLine()
        appendLine("Alert ID '$alertId' doesn't exist or doesn't belong to you.")
        appendLine()
        appendLine("Please provide a valid alert ID or use $CMD_LIST_ALERTS to see your alerts.")
    }

    fun getEditAlertDetailsWithCurrentMessage(
        alertId: String,
        existingAlert: JobSearchOut
    ): String = buildString {
        appendLine("✏️ <b>Editing Alert: $alertId</b>")
        appendLine()
        appendLine("<b>Current Alert Details:</b>")
        appendLine()
        append(existingAlert.toMessage())
        appendLine("─".repeat(40))
        appendLine()
        appendLine("Please provide the new job search criteria:")
        appendLine()
        append(getJobSearchFormattingInstructions())
        appendLine()
        appendLine("Use $CMD_CANCEL to abort this operation.")
    }

    fun getEditConfirmationMessage(alertId: String, jobSearch: JobSearchIn): String = buildString {
        appendLine("✅ <b>Updated job search parsed successfully!</b>")
        appendLine()
        appendLine("<b>Alert ID:</b> $alertId")
        appendLine()
        append(getJobSearchDetails(jobSearch))
        appendLine()
        appendLine("⏰ <b>Alert Frequency:</b> ${jobSearch.timePeriod.displayName}")
        appendLine()
        appendLine("<b>Is this correct?</b>")
        appendLine("• Reply '<b>yes</b>' to save the changes")
        appendLine("• Reply '<b>no</b>' to modify your criteria")
        appendLine("• Use $CMD_CANCEL to abort")
    }

    fun getEditSuccessMessage(alertId: String, updatedJobSearch: JobSearchOut): String =
        buildString {
            appendLine("✅ <b>Job alert updated successfully!</b>")
            appendLine()
            appendLine("📋 <b>Alert ID:</b> $alertId")
            appendLine("🔍 <b>Searching for:</b> ${updatedJobSearch.jobTitle}")
            appendLine("📍 <b>Location:</b> ${updatedJobSearch.location}")
            appendLine("⏰ <b>Frequency:</b> ${updatedJobSearch.timePeriod.displayName}")
            appendLine()
            appendLine("🔔 Your updated alert is now active and will search for jobs with the new criteria.")
            appendLine()
            appendLine("Use $CMD_LIST_ALERTS to see all your alerts or $CMD_MENU for other options.")
        }

    fun getEditRetryMessage(): String = buildString {
        appendLine("📝 <b>Let's modify your job search criteria.</b>")
        appendLine()
        append(getJobSearchFormattingInstructions())
    }

    fun getEditMaxAttemptsMessage(): String = buildString {
        appendLine("❌ <b>Unable to parse your job search criteria after multiple attempts.</b>")
        appendLine()
        appendLine("Please ensure you follow the format guidelines:")
        appendLine()
        append(getJobSearchFormattingInstructions())
        appendLine()
        appendLine("Use $CMD_CANCEL to abort this operation or try again with a clearer description.")
    }

    fun getEditParseErrorMessage(parseResult: JobSearchParseResult, retryCount: Int): String =
        buildString {
            appendLine("❌ <b>Unable to parse your job search criteria.</b> (Attempt $retryCount/3)")
            appendLine()
            if (parseResult.errorMessage?.isNotBlank() ?: false) {
                appendLine("<b>Error:</b> ${parseResult.errorMessage}")
                appendLine()
            }
            appendLine("Please try again with a clearer description:")
            appendLine()
            append(getJobSearchFormattingInstructions())
            appendLine()
            appendLine("Use $CMD_CANCEL to abort this operation.")
        }
} 