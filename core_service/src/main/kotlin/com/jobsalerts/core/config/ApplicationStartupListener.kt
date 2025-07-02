package com.jobsalerts.core.config

import com.jobsalerts.core.service.JobSearchScheduler
import com.jobsalerts.core.service.JobSearchService
import com.jobsalerts.core.service.ScraperClient
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.boot.context.event.ApplicationReadyEvent
import org.springframework.context.event.EventListener
import org.springframework.stereotype.Component
import kotlinx.coroutines.runBlocking

@Component
class ApplicationStartupListener(
    private val jobSearchScheduler: JobSearchScheduler,
    private val jobSearchService: JobSearchService,
    private val scraperClient: ScraperClient
) : Logging {
    
    @EventListener(ApplicationReadyEvent::class)
    fun onApplicationReady() = runBlocking {
        try {
            logger.info { "Application startup - initializing services" }

            // Check scraper service connection
            try {
                val health = scraperClient.checkHealth()
                logger.info { "Scraper service health check: $health" }
            } catch (e: Exception) {
                logger.warn(e) { "Scraper service health check failed - service may not be available" }
            }
            
            // Check proxy connection through scraper service
            try {
                val proxyCheck = scraperClient.checkProxyConnection()
                logger.info { "Proxy connection check: $proxyCheck" }
                
                val isProxyWorking = proxyCheck["success"] as? Boolean ?: false
                if (isProxyWorking) {
                    logger.info { "✅ Proxy connection is working properly" }
                } else {
                    logger.warn { "⚠️ Proxy connection failed: ${proxyCheck["message"]}" }
                }
            } catch (e: Exception) {
                logger.error(e) { "❌ Error checking proxy connection - scraper service may not be available" }
            }
            
            // Initialize job search service
            jobSearchService.initialize()
            
            logger.info { "Application startup completed successfully" }
            
        } catch (e: Exception) {
            logger.error(e) { "Error during application startup" }
        }
    }
} 