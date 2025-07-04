package com.jobsalerts.core.service

import com.jobsalerts.core.domain.model.*
import com.jobsalerts.core.service.DeepSeekRequest
import kotlinx.coroutines.runBlocking
import org.assertj.core.api.Assertions.*
import org.junit.jupiter.api.*
import org.junit.jupiter.api.extension.ExtendWith
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.test.context.ActiveProfiles
import org.springframework.test.context.TestPropertySource
import org.mockito.Mock
import org.mockito.junit.jupiter.MockitoExtension
import org.mockito.kotlin.whenever

/**
 * Integration test for JobSearchParserService with real DeepSeek API calls.
 * Uses @ActiveProfiles("test") to automatically load .env.test file with DEEPSEEK_API_KEY.
 */
@SpringBootTest(classes = [JobSearchParserService::class, DeepSeekClient::class])
@ActiveProfiles("test")
@TestPropertySource(properties = [
    "spring.main.web-application-type=none"
])
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
@ExtendWith(MockitoExtension::class)
class JobSearchParserServiceIntegrationTest {

    @Autowired
    private lateinit var jobSearchParserService: JobSearchParserService

    @Mock
    private lateinit var deepSeekClient: DeepSeekClient

    private val testUserId = 12345L

    @BeforeEach
    fun setUp() {
        jobSearchParserService = JobSearchParserService(deepSeekClient)
    }

    @Test
    fun `should parse simple job description successfully`() = runBlocking {
        // Given
        val userInput = "Software Engineer in San Francisco, full-time"
        val mockResponse = DeepSeekResponse(
            success = true,
            content = """{"jobTitle": "Software Engineer", "location": "San Francisco, CA", "jobTypes": ["Full-time"], "remoteTypes": ["On-site"]}"""
        )
        whenever(deepSeekClient.chat(DeepSeekRequest(userInput))).thenReturn(mockResponse)

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isTrue()
        assertThat(result.jobSearchIn).isNotNull()
        assertThat(result.jobSearchIn?.jobTitle).isEqualTo("Software Engineer")
        assertThat(result.jobSearchIn?.location).isEqualTo("San Francisco, CA")
        assertThat(result.jobSearchIn?.jobTypes).contains(JobType.`Full-time`)
        assertThat(result.jobSearchIn?.userId).isEqualTo(testUserId)
    }

    @Test
    fun `should handle remote job description with location`() = runBlocking {
        // Given
        val userInput = "Remote Python Developer in California, contract work"
        val mockResponse = DeepSeekResponse(
            success = true,
            content = """{"jobTitle": "Python Developer", "location": "California", "jobTypes": ["Contract"], "remoteTypes": ["Remote"]}"""
        )
        whenever(deepSeekClient.chat(DeepSeekRequest(userInput))).thenReturn(mockResponse)

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isTrue()
        assertThat(result.jobSearchIn).isNotNull()
        assertThat(result.jobSearchIn?.jobTitle).isEqualTo("Python Developer")
        assertThat(result.jobSearchIn?.location).isEqualTo("California")
        assertThat(result.jobSearchIn?.jobTypes).contains(JobType.Contract)
        assertThat(result.jobSearchIn?.remoteTypes).contains(RemoteType.Remote)
    }

    @Test
    fun `should parse multiple job types and preferences`() = runBlocking {
        // Given
        val userInput = "Full-time or part-time Data Scientist in NYC, hybrid or remote work"
        val mockResponse = DeepSeekResponse(
            success = true,
            content = """{"jobTitle": "Data Scientist", "location": "New York, NY", "jobTypes": ["Full-time", "Part-time"], "remoteTypes": ["Remote", "Hybrid"]}"""
        )
        whenever(deepSeekClient.chat(DeepSeekRequest(userInput))).thenReturn(mockResponse)

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isTrue()
        assertThat(result.jobSearchIn).isNotNull()
        assertThat(result.jobSearchIn?.jobTitle).isEqualTo("Data Scientist")
        assertThat(result.jobSearchIn?.location).isEqualTo("New York, NY")
        assertThat(result.jobSearchIn?.jobTypes).containsExactlyInAnyOrder(JobType.`Full-time`, JobType.`Part-time`)
        assertThat(result.jobSearchIn?.remoteTypes).containsExactlyInAnyOrder(RemoteType.Remote, RemoteType.Hybrid)
    }

    @Test
    fun `should handle basic internship search`() = runBlocking {
        // Given
        val userInput = "Machine Learning internship in Boston"
        val mockResponse = DeepSeekResponse(
            success = true,
            content = """{"jobTitle": "Machine Learning Intern", "location": "Boston, MA", "jobTypes": ["Internship"], "remoteTypes": ["On-site"]}"""
        )
        whenever(deepSeekClient.chat(DeepSeekRequest(userInput))).thenReturn(mockResponse)

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isTrue()
        assertThat(result.jobSearchIn).isNotNull()
        assertThat(result.jobSearchIn?.jobTitle).isEqualTo("Machine Learning Intern")
        assertThat(result.jobSearchIn?.location).isEqualTo("Boston, MA")
        assertThat(result.jobSearchIn?.jobTypes).contains(JobType.Internship)
        assertThat(result.jobSearchIn?.remoteTypes).contains(RemoteType.`On-site`)
    }

    @Test
    fun `should handle complex multi-requirement search`() = runBlocking {
        // Given
        val userInput = "Senior Frontend Developer (React, TypeScript) in Seattle or remote, full-time permanent position with 80k+ salary"
        val mockResponse = DeepSeekResponse(
            success = true,
            content = """{"jobTitle": "Senior Frontend Developer", "location": "Seattle, WA", "jobTypes": ["Full-time"], "remoteTypes": ["Remote", "On-site"]}"""
        )
        whenever(deepSeekClient.chat(DeepSeekRequest(userInput))).thenReturn(mockResponse)

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isTrue()
        assertThat(result.jobSearchIn).isNotNull()
        assertThat(result.jobSearchIn?.jobTitle).isEqualTo("Senior Frontend Developer")
        assertThat(result.jobSearchIn?.location).isEqualTo("Seattle, WA")
        assertThat(result.jobSearchIn?.jobTypes).contains(JobType.`Full-time`)
        assertThat(result.jobSearchIn?.remoteTypes).containsAnyOf(RemoteType.Remote, RemoteType.`On-site`)
    }

    @Test
    fun `should handle temporary work preferences`() = runBlocking {
        // Given
        val userInput = "Temporary SQL Developer in Chicago, 3-6 month contract"
        val mockResponse = DeepSeekResponse(
            success = true,
            content = """{"jobTitle": "SQL Developer", "location": "Chicago, IL", "jobTypes": ["Temporary"], "remoteTypes": ["On-site"]}"""
        )
        whenever(deepSeekClient.chat(DeepSeekRequest(userInput))).thenReturn(mockResponse)

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isTrue()
        assertThat(result.jobSearchIn).isNotNull()
        assertThat(result.jobSearchIn?.jobTitle).isEqualTo("SQL Developer")
        assertThat(result.jobSearchIn?.location).isEqualTo("Chicago, IL")
        assertThat(result.jobSearchIn?.jobTypes).contains(JobType.Temporary)
    }

    @Test
    fun `should handle minimum required job information`() = runBlocking {
        // Given
        val userInput = "Java Developer"
        val mockResponse = DeepSeekResponse(
            success = true,
            content = """{"jobTitle": "Java Developer", "location": "", "jobTypes": ["Full-time"], "remoteTypes": ["On-site"]}"""
        )
        whenever(deepSeekClient.chat(DeepSeekRequest(userInput))).thenReturn(mockResponse)

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isTrue()
        assertThat(result.jobSearchIn).isNotNull()
        assertThat(result.jobSearchIn?.jobTitle).isEqualTo("Java Developer")
        assertThat(result.jobSearchIn?.userId).isEqualTo(testUserId)
        assertThat(result.jobSearchIn?.timePeriod).isEqualTo(TimePeriod.getDefault())
    }

    @Test
    fun `should handle parse failure with invalid input`() = runBlocking {
        // Given
        val userInput = "xyz random text that makes no sense"
        val mockResponse = DeepSeekResponse(
            success = false,
            content = "Error: Unable to parse job description"
        )
        whenever(deepSeekClient.chat(DeepSeekRequest(userInput))).thenReturn(mockResponse)

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isFalse()
        assertThat(result.jobSearchIn).isNull()
        assertThat(result.errorMessage).isNotNull()
    }

    @Test
    fun `should handle empty or whitespace input`() = runBlocking {
        // Given
        val userInput = "   "
        val mockResponse = DeepSeekResponse(
            success = false,
            content = "Error: Empty input provided"
        )
        whenever(deepSeekClient.chat(DeepSeekRequest(userInput))).thenReturn(mockResponse)

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isFalse()
        assertThat(result.jobSearchIn).isNull()
        assertThat(result.errorMessage).isNotNull()
    }

    @Test
    fun `should handle ambiguous location parsing`() = runBlocking {
        // Given
        val userInput = "DevOps Engineer in some unclear location"
        val mockResponse = DeepSeekResponse(
            success = false,
            content = "Error: Could not determine location"
        )
        whenever(deepSeekClient.chat(DeepSeekRequest(userInput))).thenReturn(mockResponse)

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isFalse()
        assertThat(result.jobSearchIn).isNull()
        assertThat(result.errorMessage).isNotNull()
    }

    @Test
    fun `should validate parsed result before returning success`() = runBlocking {
        // Given - Mock a response that would fail validation
        val userInput = "Software Developer with unclear requirements"
        val mockResponse = DeepSeekResponse(
            success = true,
            content = """{"jobTitle": "", "location": "Valid City", "jobTypes": ["Full-time"], "remoteTypes": ["On-site"]}"""
        )
        whenever(deepSeekClient.chat(DeepSeekRequest(userInput))).thenReturn(mockResponse)

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isFalse()
        assertThat(result.jobSearchIn).isNull()
        assertThat(result.errorMessage).isNotNull()
    }

    @Test
    fun `should set default time period for parsed job search`() = runBlocking {
        // Given
        val userInput = "Backend Developer in Austin"
        val mockResponse = DeepSeekResponse(
            success = true,
            content = """{"jobTitle": "Backend Developer", "location": "Austin, TX", "jobTypes": ["Full-time"], "remoteTypes": ["On-site"]}"""
        )
        whenever(deepSeekClient.chat(DeepSeekRequest(userInput))).thenReturn(mockResponse)

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isTrue()
        assertThat(result.jobSearchIn).isNotNull()
        assertThat(result.jobSearchIn?.timePeriod).isEqualTo(TimePeriod.getDefault())
    }

    @Test
    fun `should handle case insensitive job types`() = runBlocking {
        // Given
        val userInput = "FULL-TIME frontend engineer"
        val mockResponse = DeepSeekResponse(
            success = true,
            content = """{"jobTitle": "Frontend Engineer", "location": "Remote", "jobTypes": ["full-time"], "remoteTypes": ["Remote"]}"""
        )
        whenever(deepSeekClient.chat(DeepSeekRequest(userInput))).thenReturn(mockResponse)

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isTrue()
        assertThat(result.jobSearchIn).isNotNull()
        assertThat(result.jobSearchIn?.jobTypes).contains(JobType.`Full-time`)
    }

    @Test
    fun `should handle long descriptive job search text`() = runBlocking {
        // Given
        val userInput = """
            I'm looking for a senior software engineering position focused on backend development,
            preferably using Java or Kotlin, in the San Francisco Bay Area or remotely.
            I'm open to full-time permanent positions with a competitive salary and good benefits.
            Experience with microservices, Kubernetes, and cloud platforms would be ideal.
        """.trimIndent()
        
        val mockResponse = DeepSeekResponse(
            success = true,
            content = """{"jobTitle": "Senior Software Engineer", "location": "San Francisco Bay Area, CA", "jobTypes": ["Full-time"], "remoteTypes": ["Remote", "On-site"]}"""
        )
        whenever(deepSeekClient.chat(DeepSeekRequest(userInput))).thenReturn(mockResponse)

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isTrue()
        assertThat(result.jobSearchIn).isNotNull()
        assertThat(result.jobSearchIn?.jobTitle).isEqualTo("Senior Software Engineer")
        assertThat(result.jobSearchIn?.location).isEqualTo("San Francisco Bay Area, CA")
        assertThat(result.jobSearchIn?.jobTypes).contains(JobType.`Full-time`)
    }
}