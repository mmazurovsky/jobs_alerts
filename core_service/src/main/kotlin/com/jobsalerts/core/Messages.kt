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
    
    // === Common Actions ===
    const val ACTION_CANCEL = CMD_CANCEL
    const val CANCEL_MESSAGE = "❌ Operation cancelled."
    const val USE_CANCEL_TO_ABORT = "Use $CMD_CANCEL to abort this operation."
    
    // === Common Responses ===
    const val RESPONSE_YES = "yes"
    const val RESPONSE_NO = "no"
    const val CONFIRM_YES = "Reply '**yes**' to confirm"
    const val CONFIRM_NO = "Reply '**no**' to cancel"
    
    // === Icons and Emojis ===
    const val ICON_ALERT = "🔔"
    const val ICON_SEARCH = "🔍"
    const val ICON_DELETE = "🗑️"
    const val ICON_EDIT = "✏️"
    const val ICON_LIST = "📋"
    const val ICON_SUCCESS = "✅"
    const val ICON_ERROR = "❌"
    const val ICON_WARNING = "⚠️"
    const val ICON_LOADING = "🔄"
    const val ICON_TIME = "⏰"
    const val ICON_LOCATION = "📍"
    const val ICON_JOB = "💼"
    const val ICON_REMOTE = "🏠"
    const val ICON_FILTER = "🔍"
    const val ICON_ID = "🆔"
    const val ICON_LINK = "🔗"
    const val ICON_ROBOT = "🤖"
    const val ICON_MENU = "📋"
    const val ICON_HELP = "📖"
    const val ICON_START = "🚀"
    const val ICON_NOTE = "💡"
    
    // === Error Messages ===
    const val ERROR_GENERAL = "❌ An error occurred while processing your request. Please try again or use $CMD_CANCEL to abort."
    const val ERROR_RETRIEVAL = "❌ Error retrieving your job alerts. Please try again later."
    const val ERROR_PROCESSING = "❌ Error processing your request. Please try again later."
    const val ERROR_CREATION_FAILED = "❌ Failed to create job alert. Please try again later or contact support."
    const val ERROR_UPDATE_FAILED = "❌ Failed to update job alert. Please try again later or contact support."
    const val ERROR_DELETION_FAILED = "❌ Failed to delete alert(s). Please try again later."
    const val ERROR_NO_PENDING_ALERT = "❌ No pending job alert found. Please start over with $CMD_CREATE_ALERT"
    const val ERROR_NO_PENDING_SEARCH = "❌ No pending job search found. Please start over with $CMD_SEARCH_NOW"
    const val ERROR_DISPLAY_HELP = "❌ Error displaying help. Please try again later."
    const val ERROR_DISPLAY_WELCOME = "❌ Error displaying welcome message. Please try again later."
    const val ERROR_DISPLAY_MENU = "❌ Error displaying menu. Please try again later."
    
    // === Success Messages ===
    const val SUCCESS_PARSED = "✅ **Job search parsed successfully!**"
    const val SUCCESS_ALERT_PARSED = "✅ **Job alert parsed successfully!**"
    const val SUCCESS_UPDATED_PARSED = "✅ **Updated job search parsed successfully!**"
    
    // === Headers ===
    const val HEADER_WELCOME = "🤖 **Welcome to Job Search Alerts Bot powered by AI for prompt-based filtering! I will help you to become the first applicant for jobs that match your specific prompt.**"
    const val HEADER_MAIN_MENU = "📋 **Main Menu**"
    const val HEADER_HELP = "📖 **Job Alerts Bot - Help**"
    const val HEADER_CREATE_ALERT = "🔔 **Creating a new job alert**"
    const val HEADER_IMMEDIATE_SEARCH = "🔍 **Running an immediate job search**"
    const val HEADER_DELETE_ALERT = "🗑️ **Delete Job Alert**"
    const val HEADER_EDIT_ALERT = "✏️ **Edit Job Alert**"
    const val HEADER_YOUR_ALERTS = "📋 **Your Active Job Alerts**"
    const val HEADER_DELETE_CONFIRMATION = "🗑️ **Delete Alert Confirmation**"
    const val HEADER_INVALID_ALERT_ID = "❌ **Invalid Alert ID**"
    const val HEADER_INVALID_ALERT_IDS = "❌ **Invalid Alert ID(s)**"
    const val HEADER_JOB_SEARCH_DETAILS = "🔍 **Job Search Details:**"
    const val HEADER_EDITING_ALERT = "✏️ **Editing Alert:"
    const val HEADER_CURRENT_ALERT_DETAILS = "**Current Alert Details:**"
    const val HEADER_AVAILABLE_ACTIONS = "**Possible Actions:**"
    const val HEADER_REQUIRED_FIELDS = "**Required Fields:**"
    const val HEADER_OPTIONAL_FIELDS = "**Optional Fields:**"
    const val HEADER_EXAMPLES = "**Examples:**"
    const val HEADER_EXAMPLE_DESCRIPTIONS = "**Example Descriptions:**"
    
    // === Section Dividers ===
    const val DIVIDER_40 = "────────────────────────────────────────"
    
    // === Structured Approach Template ===
    const val STRUCTURED_APPROACH_HEADER = "Let's try a structured approach. Please provide:"
    const val STRUCTURED_JOB_TITLE = "**Job Title:** [What position are you looking for?]"
    const val STRUCTURED_LOCATION = "**Location:** [Where do you want to work?]"
    const val STRUCTURED_JOB_TYPE = "**Job Type:** [Full-time, Part-time, Contract, etc.]"
    const val STRUCTURED_REMOTE_TYPE = "**Remote Type:** [Remote, On-site, Hybrid]"
    const val STRUCTURED_REQUIREMENTS = "**Additional Requirements:** [Any other requirements or keywords]"
    
    // === Common Instructions ===
    const val INSTRUCTION_IS_CORRECT = "**Is this correct?**"
    const val INSTRUCTION_RETRY_DESCRIPTION = "Please try again with a clearer description:"
    const val INSTRUCTION_PROVIDE_VALID_ID = "Please provide a valid alert ID or use $CMD_LIST_ALERTS to see your alerts."
    const val INSTRUCTION_USE_LIST_ALERTS = "Use $CMD_LIST_ALERTS to see your alerts or $CMD_CANCEL to abort."
    
    // === Notes ===
    const val NOTE_RECURRING_ALERT = "💡 **Note:** This will create a recurring alert that searches for jobs automatically!"
    const val NOTE_ONE_TIME_SEARCH = "💡 **Note:** This is a one-time search that will start executing immediately!"
    const val NOTE_RESULTS_NOTIFICATION = "🔔 You'll receive notifications when new jobs matching your criteria are found."
    const val NOTE_CANNOT_UNDO = "⚠️ **Warning:** This action cannot be undone!"
    const val NOTE_SEARCH_RUNNING = "⏳ Your job search is now running. Results will be sent to you once the search is complete in few minutes."
    const val NOTE_UPDATED_ALERT_ACTIVE = "🔔 Your updated alert is now active and will search for jobs with the new criteria."
    
    // === Menu Items ===
    const val MENU_SEARCH_NOW = "$CMD_SEARCH_NOW - 🔍 Search jobs immediately with AI"
    const val MENU_CREATE_ALERT = "$CMD_CREATE_ALERT - 🔔 Create new job alert with AI"
    const val MENU_LIST_ALERTS = "$CMD_LIST_ALERTS - 📋 View your created alerts"
    const val MENU_EDIT_ALERT = "$CMD_EDIT_ALERT - ✏️ Edit a created alert"
    const val MENU_DELETE_ALERT = "$CMD_DELETE_ALERT - 🗑️ Delete an alert"

    const val MENU_HELP = "$CMD_HELP - 📖 Detailed help"
    const val MENU_START = "$CMD_START - 🏠 Welcome message"
    
    // === Command Examples ===
    // const val EXAMPLE_EDIT_ALERT = "$CMD_EDIT_ALERT [ID] - Edit a specific alert"
    // const val EXAMPLE_DELETE_ALERT = "$CMD_DELETE_ALERT [ID] - Delete a specific alert"
    // const val EXAMPLE_CREATE_ALERT = "$CMD_CREATE_ALERT - Create a new alert"
    // const val EXAMPLE_SEARCH_NOW = "$CMD_SEARCH_NOW - Run an immediate search"
    // const val EXAMPLE_LIST_ALERTS = "$CMD_LIST_ALERTS - See all your alerts"
    const val EXAMPLE_MENU = "$CMD_MENU for other options"
    
    // === Loading Messages ===
    const val ANALYZING_DESCRIPTION = "🔍 Analyzing your job alert description..."
    const val ANALYZING_SEARCH = "🔍 Analyzing your job search description..."
    const val ANALYZING_UPDATE = "🔍 Analyzing your updated job search..."
    const val CREATING_ALERT = "🔔 **Creating your job alert...**"
    const val UPDATING_ALERT = "✏️ **Updating your job alert...**"
    const val STARTING_SEARCH = "🚀 **Starting your job search...**"
    
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
        appendLine("$CMD_CANCEL - Cancel current operation")
        appendLine()
        appendLine("Type any command like $CMD_CREATE_ALERT or $CMD_SEARCH_NOW to get started!")
    }
    
    fun getMainMenuMessage(): String = buildString {
        appendLine(HEADER_MAIN_MENU)
        appendLine()
        appendLine("Choose what you'd like to do:")
        appendLine()
        appendLine("**Search Jobs Immediately without creating an alert for new job postings:**")
        appendLine(MENU_SEARCH_NOW)
        appendLine()
        appendLine("**Job Alert Management:**")
        appendLine(MENU_CREATE_ALERT)
        appendLine(MENU_LIST_ALERTS)
        appendLine(MENU_EDIT_ALERT)
        appendLine(MENU_DELETE_ALERT)
        appendLine()
        appendLine("**Help & Info:**")
        appendLine(MENU_HELP)
        appendLine()
        appendLine("Just use any command to get started!")
    }
    
    fun getHelpMessage(): String = buildString {
        appendLine(HEADER_HELP)
        appendLine()
        appendLine("**Main Commands:**")
        appendLine("$CMD_START - Welcome message and command overview")
        appendLine("$CMD_MENU - Show main menu with quick options")
        appendLine("$CMD_HELP - Show this help message")
        appendLine("$CMD_CANCEL - Cancel current operation")
        appendLine()
        appendLine("**Job Alert Management:**")
        appendLine("$CMD_CREATE_ALERT - 🔔 Create a new job search alert")
        appendLine("$CMD_LIST_ALERTS - 📋 View all your active job alerts")
        appendLine("$CMD_EDIT_ALERT - ✏️ Modify an existing job alert")
        appendLine("$CMD_DELETE_ALERT - 🗑️ Remove a job alert")
        appendLine()
        appendLine("**Job Search:**")
        appendLine("$CMD_SEARCH_NOW - 🔍 Run an immediate one-time job search")
        appendLine()
        appendLine("**How to use:**")
        appendLine("• Simply type the command (e.g., $CMD_CREATE_ALERT)")
        appendLine("• Add parameters if needed (e.g., $CMD_EDIT_ALERT 123)")
        appendLine("• Follow the prompts for interactive setup")
        appendLine()
        appendLine("**Examples:**")
        appendLine("• $CMD_CREATE_ALERT - Start creating a new alert")
        appendLine("• $CMD_LIST_ALERTS - See all your alerts")
        appendLine("• $CMD_SEARCH_NOW python berlin - Search for Python jobs in Berlin")
        appendLine("• $CMD_DELETE_ALERT 123 - Delete alert with ID 123")
        appendLine()
        appendLine("**Job Search Format:**")
        appendLine("When creating or editing alerts, you can describe your job requirements in natural language:")
        appendLine()
        appendLine("\"Looking for Senior Python Developer in Berlin, remote work possible, salary 80k+, no startups\"")
        appendLine()
        appendLine("The system will automatically parse:")
        appendLine("• Job Title: Senior Python Developer")
        appendLine("• Location: Berlin")
        appendLine("• Remote: Yes")
        appendLine("• Salary: 80k+")
        appendLine("• Filter: No startups")
        appendLine()
        appendLine("**Alert Frequency:**")
        appendLine("You can specify how often to search:")
        appendLine("• Daily")
        appendLine("• Weekly")
        appendLine("• Monthly")
        appendLine()
        appendLine("**Need More Help?**")
        appendLine("If you encounter any issues or need assistance, feel free to reach out or try $CMD_MENU for quick access to all functions!")
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
        appendLine("• Reply '**yes**' to create the alert")
        appendLine("• Reply '**no**' to modify your alert")
        appendLine("• Use $CMD_CANCEL to abort")
    }
    
    fun getSearchConfirmation(jobSearch: JobSearchIn): String = buildString {
        appendLine(SUCCESS_PARSED)
        appendLine()
        append(jobSearch.toHumanReadableString())
        appendLine()
        appendLine(INSTRUCTION_IS_CORRECT)
        appendLine("• Reply '**yes**' to proceed with the search")
        appendLine("• Reply '**no**' to modify your search")
        appendLine("• Use $CMD_CANCEL to abort")
    }
    
    fun getEditConfirmation(alertId: String, jobSearch: JobSearchIn): String = buildString {
        appendLine(SUCCESS_UPDATED_PARSED)
        appendLine()
        appendLine("**Alert ID:** $alertId")
        appendLine()
        append(jobSearch.toHumanReadableString())
        appendLine()
        appendLine(INSTRUCTION_IS_CORRECT)
        appendLine("• Reply '**yes**' to save the changes")
        appendLine("• Reply '**no**' to modify your criteria")
        appendLine("• Use $CMD_CANCEL to abort")
    }
    
    // === Success Messages ===
    fun getAlertCreatedSuccess(alertId: String, jobSearch: JobSearchIn): String = buildString {
        appendLine("✅ **Job alert created successfully!**")
        appendLine()
        appendLine("$ICON_ID **Alert ID:** $alertId")
        appendLine("🔍 **Searching for:** ${jobSearch.jobTitle}")
        appendLine("📍 **Location:** ${jobSearch.location}")
        appendLine("⏰ **Frequency:** ${jobSearch.timePeriod.displayName}")
        appendLine()
        appendLine(NOTE_RESULTS_NOTIFICATION)
        appendLine()
        appendLine("Use $CMD_LIST_ALERTS to see all your alerts or $CMD_MENU for other options.")
    }
    
    fun getSearchInitiatedSuccess(searchId: String, jobSearch: JobSearchIn): String = buildString {
        appendLine("✅ **Job search initiated successfully!**")
        appendLine()
        appendLine("📋 **Search ID:** $searchId")
        appendLine("🔍 **Searching for:** ${jobSearch.jobTitle}")
        appendLine("📍 **Location:** ${jobSearch.location}")
        appendLine()
        appendLine(NOTE_SEARCH_RUNNING)
        appendLine()
        appendLine("Use $CMD_MENU to access other options.")
    }
    
    fun getAlertUpdatedSuccess(alertId: String, jobSearch: JobSearchIn): String = buildString {
        appendLine("✅ **Job alert updated successfully!**")
        appendLine()
        appendLine("📋 **Alert ID:** $alertId")
        appendLine("🔍 **Searching for:** ${jobSearch.jobTitle}")
        appendLine("📍 **Location:** ${jobSearch.location}")
        appendLine("⏰ **Frequency:** ${jobSearch.timePeriod.displayName}")
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
        appendLine("**Get started:**")
        appendLine("$CMD_CREATE_ALERT - Create your first job alert")
        appendLine("$CMD_HELP - See all available commands")
    }
    
    fun getSelectAlertToDeleteMessage(userSearches: List<JobSearchOut>): String = buildString {
        appendLine(HEADER_DELETE_ALERT)
        appendLine()
        appendLine("Which alert(s) would you like to delete? Please provide the alert ID(s).")
        appendLine()
        appendLine("**Your Active Job Alerts:**")
        appendLine()
        
        userSearches.forEach { jobSearch ->
            append(jobSearch.toMessage())
            appendLine(DIVIDER_40)
            appendLine()
        }
        
        appendLine(HEADER_EXAMPLES)
        appendLine("• `123` - Delete alert with ID 123")
        appendLine("• `123,456` - Delete alerts with IDs 123 and 456")
        appendLine()
        appendLine(USE_CANCEL_TO_ABORT)
    }
    
    fun getDeleteConfirmationMessage(validAlertIds: List<String>): String = buildString {
        appendLine(HEADER_DELETE_CONFIRMATION)
        appendLine()
        if (validAlertIds.size == 1) {
            appendLine("Are you sure you want to delete alert: **${validAlertIds[0]}**?")
        } else {
            appendLine("Are you sure you want to delete these ${validAlertIds.size} alerts?")
            validAlertIds.forEach { appendLine("• **$it**") }
        }
        appendLine()
        appendLine(NOTE_CANNOT_UNDO)
        appendLine()
        appendLine("• Reply '**yes**' to confirm deletion")
        appendLine("• Reply '**no**' to cancel")
        appendLine("• Use $CMD_CANCEL to abort this operation")
    }
    
    fun getInvalidAlertIdsMessage(invalidAlertIds: List<String>, validAlertIds: List<String>): String = buildString {
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
    
    fun getDeletionResultMessage(deletedIds: List<String>, failedIds: List<String>): String = buildString {
        if (deletedIds.isNotEmpty()) {
            if (deletedIds.size == 1) {
                appendLine("✅ **Alert ${deletedIds[0]} has been deleted successfully.**")
            } else {
                appendLine("✅ **${deletedIds.size} alerts have been deleted successfully:**")
                deletedIds.forEach { appendLine("• $it") }
            }
        }
        
        if (failedIds.isNotEmpty()) {
            appendLine()
            appendLine("❌ **Failed to delete the following alert(s):**")
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
        appendLine("**Get started:**")
        appendLine("$CMD_CREATE_ALERT - Create your first job alert")
        appendLine("$CMD_HELP - See all available commands")
    }
    
    fun getSelectAlertToEditMessage(userSearches: List<JobSearchOut>): String = buildString {
        appendLine(HEADER_EDIT_ALERT)
        appendLine()
        appendLine("Which alert would you like to edit? Please provide the alert ID.")
        appendLine()
        appendLine("**Your Active Job Alerts:**")
        appendLine()
        
        userSearches.forEach { jobSearch ->
            append(jobSearch.toMessage())
            appendLine(DIVIDER_40)
            appendLine()
        }
        
        appendLine("**Example:** `123` (just the ID number)")
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
    
    fun getEditAlertDetailsMessage(alertId: String, existingAlert: JobSearchOut): String = buildString {
        appendLine("$HEADER_EDITING_ALERT $alertId**")
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
        appendLine("**Get started:**")
        appendLine("$CMD_CREATE_ALERT - Create your first job alert")
        appendLine("$CMD_HELP - See all available commands")
        appendLine()
        appendLine("Ready to find your next opportunity? 🚀")
    }
    
    fun getActiveAlertsMessage(userSearches: List<JobSearchOut>): String = buildString {
        appendLine("$HEADER_YOUR_ALERTS (${userSearches.size} total)\n")
        
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
        appendLine("📝 **Let's modify your job search.**")
        appendLine()
        append(JobSearchIn.getFormattingInstructions())
    }
    
    fun getRetryJobAlertMessage(): String = buildString {
        appendLine("📝 **Let's modify your job alert.**")
        appendLine()
        append(JobSearchIn.getFormattingInstructions())
    }
    
    fun getStructuredApproachMessage(): String = buildString {
        appendLine("❌ **I'm having trouble understanding your job search description.**")
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
        appendLine("❌ **${parseResult.errorMessage}**")
        appendLine()
        if (parseResult.missingFields.isNotEmpty()) {
            appendLine("**Missing information:** ${parseResult.missingFields.joinToString(", ")}")
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
        appendLine("❌ **${parseResult.errorMessage}**")
        appendLine()
        if (parseResult.missingFields.isNotEmpty()) {
            appendLine("**Missing information:** ${parseResult.missingFields.joinToString(", ")}")
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
        appendLine("🔔 New job listings found for your search.\n")
        jobs.forEach { job ->
            appendLine(job.toMessage())
            appendLine()
        }
    }
    
    // === Common Confirmation Responses ===
    fun getConfirmationInstruction(actionType: String): String = when (actionType) {
        "create" -> "Please respond with '**yes**' to create the alert, '**no**' to edit description again, or $CMD_CANCEL to abort."
        "delete" -> "Please respond with '**yes**' to delete the alert(s), '**no**' to cancel, or $CMD_CANCEL to abort."
        "edit" -> "Please respond with '**yes**' to save the changes, '**no**' to modify changes again, or $CMD_CANCEL to abort."
        "search" -> "Please respond with '**yes**' to proceed, '**no**' to modify description again, or $CMD_CANCEL to abort."
        else -> "Please respond with '**yes**' to proceed, '**no**' to cancel, or $CMD_CANCEL to abort."
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
} 