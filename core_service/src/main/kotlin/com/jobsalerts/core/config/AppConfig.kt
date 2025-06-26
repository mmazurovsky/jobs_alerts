package com.jobsalerts.core.config

import org.springframework.boot.context.properties.ConfigurationProperties
import org.springframework.boot.context.properties.EnableConfigurationProperties
import org.springframework.context.annotation.Configuration

@Configuration
@EnableConfigurationProperties(
    TelegramConfig::class,
    AdminConfig::class,
    DeepSeekConfig::class,
    CallbackConfig::class,
    ScraperConfig::class
)
class AppConfig

@ConfigurationProperties(prefix = "telegram.bot")
data class TelegramConfig(
    val token: String
)

@ConfigurationProperties(prefix = "admin.user")
data class AdminConfig(
    val id: Int
)

@ConfigurationProperties(prefix = "deepseek.api")
data class DeepSeekConfig(
    val key: String?
)

@ConfigurationProperties(prefix = "callback")
data class CallbackConfig(
    val url: String = "http://localhost:8080"
)

@ConfigurationProperties(prefix = "scraper.service")
data class ScraperConfig(
    val url: String = "http://localhost:8000"
) 