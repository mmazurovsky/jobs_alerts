package com.jobsalerts.core.service

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import com.jobsalerts.core.config.DeepSeekConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.apache.logging.log4j.kotlin.Logging
import org.springframework.stereotype.Service
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.time.Duration

data class DeepSeekRequest(
    val prompt: String,
    val temperature: Double = 0.1,
    val maxTokens: Int = 500,
    val model: String = "deepseek-chat"
)

data class DeepSeekResponse(
    val success: Boolean,
    val content: String? = null,
    val errorMessage: String? = null,
    val statusCode: Int? = null
)

@Service
class DeepSeekClient(
    private val deepSeekConfig: DeepSeekConfig
) : Logging {

    private val httpClient = HttpClient.newBuilder()
        .connectTimeout(Duration.ofSeconds(30))
        .build()
    
    private val objectMapper: ObjectMapper = jacksonObjectMapper()

    suspend fun chat(request: DeepSeekRequest): DeepSeekResponse {
        return withContext(Dispatchers.IO) {
            try {
                if (deepSeekConfig.key.isNullOrBlank()) {
                    return@withContext DeepSeekResponse(
                        success = false,
                        errorMessage = "DeepSeek API key not configured"
                    )
                }

                val response = callAPI(request)
                
                if (response.statusCode() == 200) {
                    val content = parseSuccessResponse(response.body())
                    DeepSeekResponse(success = true, content = content)
                } else {
                    logger.error { "DeepSeek API error: ${response.statusCode()} - ${response.body()}" }
                    DeepSeekResponse(
                        success = false,
                        errorMessage = "API request failed with status ${response.statusCode()}",
                        statusCode = response.statusCode()
                    )
                }
            } catch (e: Exception) {
                logger.error(e) { "Error calling DeepSeek API" }
                DeepSeekResponse(
                    success = false,
                    errorMessage = "Failed to call DeepSeek API: ${e.message}"
                )
            }
        }
    }

    private suspend fun callAPI(request: DeepSeekRequest): HttpResponse<String> {
        val requestBody = objectMapper.writeValueAsString(mapOf(
            "model" to request.model,
            "messages" to listOf(
                mapOf(
                    "role" to "user",
                    "content" to request.prompt
                )
            ),
            "temperature" to request.temperature,
            "max_tokens" to request.maxTokens
        ))

        val httpRequest = HttpRequest.newBuilder()
            .uri(URI.create("https://api.deepseek.com/chat/completions"))
            .header("Content-Type", "application/json")
            .header("Authorization", "Bearer ${deepSeekConfig.key}")
            .POST(HttpRequest.BodyPublishers.ofString(requestBody))
            .build()

        return httpClient.send(httpRequest, HttpResponse.BodyHandlers.ofString())
    }

    private fun parseSuccessResponse(responseBody: String): String {
        val responseJson = objectMapper.readTree(responseBody)
        return responseJson.path("choices").get(0).path("message").path("content").asText()
    }

    fun isAvailable(): Boolean {
        return !deepSeekConfig.key.isNullOrBlank()
    }
} 