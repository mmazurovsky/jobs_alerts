package com.jobsalerts.core.config

import com.jobsalerts.core.service.ScraperClient
import kotlinx.coroutines.runBlocking
import org.springframework.boot.actuate.health.Health
import org.springframework.boot.actuate.health.HealthIndicator
import org.springframework.data.mongodb.core.MongoTemplate
import org.springframework.stereotype.Component

@Component("mongodb")
class MongoHealthIndicator(
    private val mongoTemplate: MongoTemplate
) : HealthIndicator {
    
    override fun health(): Health {
        return try {
            mongoTemplate.db.runCommand(org.bson.Document("ping", 1))
            Health.up()
                .withDetail("database", mongoTemplate.db.name)
                .build()
        } catch (e: Exception) {
            Health.down()
                .withException(e)
                .build()
        }
    }
}

@Component("scraperService")
class ScraperServiceHealthIndicator(
    private val scraperClient: ScraperClient
) : HealthIndicator {
    
    override fun health(): Health {
        return try {
            val result = runBlocking {
                scraperClient.checkProxyConnection()
            }
            
            if (result["success"] == true) {
                Health.up()
                    .withDetail("message", result["message"])
                    .build()
            } else {
                Health.down()
                    .withDetail("message", result["message"])
                    .build()
            }
        } catch (e: Exception) {
            Health.down()
                .withException(e)
                .withDetail("message", "Unable to connect to scraper service")
                .build()
        }
    }
} 