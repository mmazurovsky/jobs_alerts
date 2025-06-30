package com.jobsalerts.core.config

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.databind.SerializationFeature
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule
import com.fasterxml.jackson.module.kotlin.kotlinModule
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.context.annotation.Primary

@Configuration
class BeanConfig {
    // Spring Events will be handled automatically by ApplicationEventPublisher
    // No need for manual StreamManager bean

    @Bean
    @Primary
    fun objectMapper(): ObjectMapper =
        ObjectMapper()
            .registerModules(
                kotlinModule(),          // Kotlin data-class & null-handling
                JavaTimeModule(),        // java.time.* support
            )
            .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS) // ISO-8601
} 