package com.jobsalerts.core.domain.model

enum class JobType {
    `Full-time`,
    `Part-time`,
    Contract,
    Temporary,
    Internship;

    val label: String
        get() = name

    companion object {
        fun fromLabel(label: String): JobType? {
            return values().find { it.name.equals(label, ignoreCase = true) }
        }

        fun getDefault(): JobType = `Full-time`

        fun getAllLabels(): List<String> = values().map { it.name }
    }
} 