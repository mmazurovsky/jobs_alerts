package com.jobsalerts.core.config

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import com.mongodb.client.MongoClient
import com.mongodb.client.MongoClients
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.core.convert.converter.Converter
import org.springframework.data.mongodb.MongoDatabaseFactory
import org.springframework.data.mongodb.config.AbstractMongoClientConfiguration
import org.springframework.data.mongodb.core.MongoTemplate
import org.springframework.data.mongodb.core.SimpleMongoClientDatabaseFactory
import org.springframework.data.mongodb.core.convert.DefaultMongoTypeMapper
import org.springframework.data.mongodb.core.convert.MappingMongoConverter
import org.springframework.data.mongodb.core.convert.MongoCustomConversions
import org.springframework.data.mongodb.core.mapping.MongoMappingContext
import org.springframework.data.mongodb.repository.config.EnableMongoRepositories
import java.time.Instant
import java.time.OffsetDateTime
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.time.format.DateTimeParseException
import java.util.*

@Configuration
@EnableMongoRepositories(basePackages = ["com.jobsalerts.core.repository"])
class MongoConfig {

    @Bean
    fun mappingMongoConverter(
        databaseFactory: MongoDatabaseFactory,
        customConversions: MongoCustomConversions,
        mappingContext: MongoMappingContext
    ): MappingMongoConverter {
        val converter = MappingMongoConverter(databaseFactory, mappingContext)
        converter.setCustomConversions(customConversions)
        // Remove the _class field from documents
        converter.setTypeMapper(DefaultMongoTypeMapper(null))
        return converter
    }

    @Bean
    fun mongoCustomConversions(): MongoCustomConversions {
        return MongoCustomConversions(
            listOf(
                OffsetDateTimeWriteConverter(),
                OffsetDateTimeReadConverter(),
            )
        )
    }
}

class OffsetDateTimeReadConverter : Converter<Date?, OffsetDateTime?> {
    override fun convert(date: Date): OffsetDateTime {
        return date.toInstant().atOffset(ZoneOffset.UTC).withNano(0)
    }
}

class OffsetDateTimeWriteConverter : Converter<OffsetDateTime?, Date?> {
    override fun convert(offsetDateTime: OffsetDateTime): Date {
        return Date.from(offsetDateTime.withNano(0).toInstant())
    }
}
