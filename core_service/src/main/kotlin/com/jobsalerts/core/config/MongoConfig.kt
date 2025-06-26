package com.jobsalerts.core.config

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.data.mongodb.config.AbstractMongoClientConfiguration
import org.springframework.data.mongodb.core.convert.MongoCustomConversions
import org.springframework.data.mongodb.repository.config.EnableMongoRepositories

@Configuration
@EnableMongoRepositories(basePackages = ["com.jobsalerts.core.repository"])
class MongoConfig : AbstractMongoClientConfiguration() {

    override fun getDatabaseName(): String = "jobs_alerts"

    @Bean
    override fun customConversions(): MongoCustomConversions {
        return MongoCustomConversions(emptyList<Any>())
    }

    @Bean
    fun mongoObjectMapper(): ObjectMapper {
        return jacksonObjectMapper().apply {
            findAndRegisterModules()
        }
    }
} 