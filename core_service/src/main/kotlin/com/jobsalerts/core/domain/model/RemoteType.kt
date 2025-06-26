package com.jobsalerts.core.domain.model

enum class RemoteType(val label: String) {
    ON_SITE("On-site"),
    REMOTE("Remote"),
    HYBRID("Hybrid");

    companion object {
        fun fromLabel(label: String): RemoteType? {
            return values().find { it.label.equals(label, ignoreCase = true) }
        }

        fun getDefault(): RemoteType = REMOTE

        fun getAllLabels(): List<String> = values().map { it.label }
    }
} 