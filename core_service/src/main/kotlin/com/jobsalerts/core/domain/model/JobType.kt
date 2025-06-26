package com.jobsalerts.core.domain.model

enum class JobType(val label: String) {
    FULL_TIME("Full-time"),
    PART_TIME("Part-time"),
    CONTRACT("Contract"),
    TEMPORARY("Temporary"),
    INTERNSHIP("Internship");

    companion object {
        fun fromLabel(label: String): JobType? {
            return values().find { it.label.equals(label, ignoreCase = true) }
        }

        fun getDefault(): JobType = FULL_TIME

        fun getAllLabels(): List<String> = values().map { it.label }
    }
} 