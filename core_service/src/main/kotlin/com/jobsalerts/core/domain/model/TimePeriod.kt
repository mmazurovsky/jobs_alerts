package com.jobsalerts.core.domain.model

import org.quartz.CronScheduleBuilder
import org.quartz.CronTrigger
import org.quartz.TriggerBuilder

enum class TimePeriod(
    val seconds: Int,
    val cronExpression: String,
    val maxPagesToScrape: Int,
    val linkedinCode: String
) {
    `5 minutes`(300, "0 0/5 * * * ?", 1, "r300"),
    `10 minutes`(600, "0 0/10 * * * ?", 2, "r600"),
    `15 minutes`(900, "0 0/15 * * * ?", 3, "r900"),
    `20 minutes`(1200, "0 0/20 * * * ?", 4, "r1200"),
    `30 minutes`(1800, "0 0/30 * * * ?", 5, "r1800"),
    `1 hour`(3600, "0 0 * * * ?", 10, "r3600"),
    `4 hours`(14400, "0 0 0/4 * * ?", 10, "r14400"),
    `24 hours`(43200, "0 0 0 * * ?", 10, "r43200"),
    `1 week`(302400, "0 0 0 ? * MON", 15, "r302400"),
    `1 month`(1209600, "0 0 0 1 * ?", 20, "r1209600");

    val displayName: String
        get() = name

    fun toHumanReadable(): String = displayName

    fun toSeconds(): Int = seconds

    fun getCronTrigger(): CronTrigger {
        return TriggerBuilder.newTrigger()
            .withSchedule(CronScheduleBuilder.cronSchedule(cronExpression))
            .build() as CronTrigger
    }

    companion object {
        fun fromDisplayName(name: String): TimePeriod? {
            return values().find { it.name.equals(name, ignoreCase = true) }
        }

        fun getDefault(): TimePeriod = `1 hour`

        fun getOneTimeSearchPeriod(): TimePeriod = `1 week`
    }
} 