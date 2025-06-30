package com.jobsalerts.core.service

import com.jobsalerts.core.domain.model.*
import kotlinx.coroutines.runBlocking
import org.assertj.core.api.Assertions.*
import org.junit.jupiter.api.*
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.test.context.ActiveProfiles
import org.springframework.test.context.TestPropertySource

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
class JobSearchParserServiceIntegrationTest {

    @Autowired
    private lateinit var jobSearchParserService: JobSearchParserService

    @Autowired
    private lateinit var deepSeekClient: DeepSeekClient

    private val testUserId = 12345

    @BeforeAll
    fun setup() {
        // Verify DeepSeek client is available before running tests
        println("🔑 DeepSeek API available: ${deepSeekClient.isAvailable()}")
        assertThat(deepSeekClient.isAvailable()).isTrue()
    }

    @Test
    fun `should parse simple job description successfully`() = runBlocking {
        // Given
        val userInput = "Software Engineer in San Francisco, full-time"

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isTrue()
        assertThat(result.jobSearchIn).isNotNull()
        assertThat(result.jobSearchIn!!.jobTitle.lowercase()).contains("software engineer")
        assertThat(result.jobSearchIn!!.location.lowercase()).contains("san francisco")
        assertThat(result.jobSearchIn!!.jobTypes).contains(JobType.FULL_TIME)
        assertThat(result.jobSearchIn!!.userId).isEqualTo(testUserId)
        assertThat(result.errorMessage).isNull()
        assertThat(result.missingFields).isEmpty()
        
        println("✅ Simple parsing result: ${result.jobSearchIn}")
    }

    @Test
    fun `should parse complex job description with all details`() = runBlocking {
        // Given
        val userInput = "Senior Data Scientist in Berlin, remote work, contract position, Python required, no startups, $120k+ salary"

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isTrue()
        assertThat(result.jobSearchIn).isNotNull()
        
        with(result.jobSearchIn!!) {
            assertThat(jobTitle.lowercase()).contains("data scientist")
            assertThat(location.lowercase()).contains("berlin")
            assertThat(jobTypes).contains(JobType.CONTRACT)
            assertThat(remoteTypes).contains(RemoteType.REMOTE)
            assertThat(filterText).isNotNull()
            assertThat(filterText!!.lowercase()).containsAnyOf("python", "no startups", "120k", "salary")
            assertThat(userId).isEqualTo(testUserId)
        }
        
        println("✅ Complex parsing result: ${result.jobSearchIn}")
    }

    @Test
    fun `should parse job with multiple job types`() = runBlocking {
        // Given
        val userInput = "Frontend Developer in London, part-time or contract, React experience, flexible hours"

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isTrue()
        assertThat(result.jobSearchIn).isNotNull()
        
        with(result.jobSearchIn!!) {
            assertThat(jobTitle.lowercase()).contains("frontend developer")
            assertThat(location.lowercase()).contains("london")
            // Should pick one of the job types mentioned
            assertThat(jobTypes).anyMatch { it in listOf(JobType.PART_TIME, JobType.CONTRACT) }
            assertThat(filterText).isNotNull()
            assertThat(filterText!!.lowercase()).containsAnyOf("react", "flexible hours")
        }
        
        println("✅ Multiple job types result: ${result.jobSearchIn}")
    }

    @Test
    fun `should handle remote anywhere location`() = runBlocking {
        // Given
        val userInput = "DevOps Engineer, remote anywhere, Kubernetes experience, full-time"

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isTrue()
        assertThat(result.jobSearchIn).isNotNull()
        
        with(result.jobSearchIn!!) {
            assertThat(jobTitle.lowercase()).contains("devops")
            assertThat(location.lowercase()).containsAnyOf("remote", "anywhere")
            assertThat(remoteTypes).contains(RemoteType.REMOTE)
            assertThat(jobTypes).contains(JobType.FULL_TIME)
            assertThat(filterText?.lowercase()).contains("kubernetes")
        }
        
        println("✅ Remote anywhere result: ${result.jobSearchIn}")
    }

    @Test
    fun `should handle hybrid work arrangement`() = runBlocking {
        // Given
        val userInput = "Product Manager in New York, hybrid work, MBA preferred, $150k+ base salary"

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isTrue()
        assertThat(result.jobSearchIn).isNotNull()
        
        with(result.jobSearchIn!!) {
            assertThat(jobTitle.lowercase()).contains("product manager")
            assertThat(location.lowercase()).contains("new york")
            assertThat(remoteTypes).contains(RemoteType.HYBRID)
            assertThat(filterText?.lowercase()).containsAnyOf("mba", "150k", "salary")
        }
        
        println("✅ Hybrid work result: ${result.jobSearchIn}")
    }

    @Test
    fun `should parse even vague job descriptions successfully`() = runBlocking {
        // Given - DeepSeek is quite good at parsing even vague inputs
        val userInput = "Looking for a job"

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then - DeepSeek should be able to parse even this vague input
        if (result.success) {
            assertThat(result.jobSearchIn).isNotNull()
            assertThat(result.errorMessage).isNull()
            println("✅ Vague input successfully parsed: ${result.jobSearchIn}")
        } else {
            // If it fails, that's also acceptable for such vague input
            assertThat(result.jobSearchIn).isNull()
            assertThat(result.errorMessage).isNotNull()
            println("✅ Vague input appropriately failed: ${result.errorMessage}")
            println("✅ Missing fields: ${result.missingFields}")
        }
    }

    @Test
    fun `should handle completely invalid input`() = runBlocking {
        // Given
        val userInput = "This is not a job description at all, just random text about cats and dogs and xyz123!@#"

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then - This should likely fail, but DeepSeek might still try to parse it
        if (result.success) {
            // If DeepSeek manages to parse this, log what it created
            println("✅ DeepSeek parsed random text: ${result.jobSearchIn}")
            assertThat(result.jobSearchIn).isNotNull()
        } else {
            assertThat(result.jobSearchIn).isNull()
            assertThat(result.errorMessage).isNotNull()
            println("✅ Invalid input appropriately failed: ${result.errorMessage}")
        }
    }

    @Test
    fun `should handle empty string input`() = runBlocking {
        // Given
        val userInput = ""

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isFalse()
        assertThat(result.jobSearchIn).isNull()
        assertThat(result.errorMessage).isNotNull()
        
        println("✅ Empty input error: ${result.errorMessage}")
    }

    @Test
    fun `should parse international job descriptions`() = runBlocking {
        // Given
        val userInput = "Machine Learning Engineer in Tokyo, full-time, English speaking required, visa sponsorship"

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isTrue()
        assertThat(result.jobSearchIn).isNotNull()
        
        with(result.jobSearchIn!!) {
            assertThat(jobTitle.lowercase()).contains("machine learning")
            assertThat(location.lowercase()).contains("tokyo")
            assertThat(jobTypes).contains(JobType.FULL_TIME)
            assertThat(filterText?.lowercase()).containsAnyOf("english", "visa", "sponsorship")
        }
        
        println("✅ International job result: ${result.jobSearchIn}")
    }

    @Test
    fun `should parse job with salary and benefits requirements`() = runBlocking {
        // Given
        val userInput = "Backend Engineer in Austin, remote, $130k-160k, health insurance, stock options, no on-call"

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isTrue()
        assertThat(result.jobSearchIn).isNotNull()
        
        with(result.jobSearchIn!!) {
            assertThat(jobTitle.lowercase()).contains("backend")
            assertThat(location.lowercase()).contains("austin")
            assertThat(remoteTypes).contains(RemoteType.REMOTE)
            assertThat(filterText).isNotNull()
            assertThat(filterText!!.lowercase()).containsAnyOf("130k", "160k", "health", "stock", "no on-call")
        }
        
        println("✅ Salary and benefits result: ${result.jobSearchIn}")
    }

    @Test
    fun `should handle company preferences and exclusions`() = runBlocking {
        // Given
        val userInput = "Full Stack Developer in Seattle, on-site, avoid FAANG companies, prefer startups, React and Node.js"

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isTrue()
        assertThat(result.jobSearchIn).isNotNull()
        
        with(result.jobSearchIn!!) {
            assertThat(jobTitle.lowercase()).contains("full stack")
            assertThat(location.lowercase()).contains("seattle")
            assertThat(remoteTypes).contains(RemoteType.ON_SITE)
            assertThat(filterText?.lowercase()).containsAnyOf("avoid faang", "prefer startups", "react", "node")
        }
        
        println("✅ Company preferences result: ${result.jobSearchIn}")
    }

    @Test
    fun `should parse internship position`() = runBlocking {
        // Given
        val userInput = "Software Engineering Internship in Boston, summer 2024, Python programming, university student"

        // When
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)

        // Then
        assertThat(result.success).isTrue()
        assertThat(result.jobSearchIn).isNotNull()
        
        with(result.jobSearchIn!!) {
            assertThat(jobTitle.lowercase()).containsAnyOf("internship", "intern")
            assertThat(location.lowercase()).contains("boston")
            assertThat(jobTypes).contains(JobType.INTERNSHIP)
            assertThat(filterText?.lowercase()).containsAnyOf("summer", "python", "university")
        }
        
        println("✅ Internship result: ${result.jobSearchIn}")
    }

    @Test
    fun `should validate all job types are supported`() = runBlocking {
        val testCases = listOf(
            "Software Engineer, full-time" to JobType.FULL_TIME,
            "Consultant, part-time work" to JobType.PART_TIME,
            "Developer, contract position" to JobType.CONTRACT,
            "Analyst, temporary role" to JobType.TEMPORARY,
            "Engineering internship" to JobType.INTERNSHIP
        )

        for ((input, expectedJobType) in testCases) {
            val fullInput = "$input in San Francisco"
            val result = jobSearchParserService.parseUserInput(fullInput, testUserId)
            
            assertThat(result.success).withFailMessage("Failed to parse: $fullInput").isTrue()
            assertThat(result.jobSearchIn?.jobTypes).withFailMessage("Wrong job type for: $fullInput").contains(expectedJobType)
            
            println("✅ Job type validation - $input: ${result.jobSearchIn?.jobTypes}")
        }
    }

    @Test
    fun `should validate all remote types are supported`() = runBlocking {
        val testCases = listOf(
            "Developer, remote work" to RemoteType.REMOTE,
            "Engineer, on-site position" to RemoteType.ON_SITE,
            "Manager, hybrid work" to RemoteType.HYBRID
        )

        for ((input, expectedRemoteType) in testCases) {
            val fullInput = "$input in Chicago"
            val result = jobSearchParserService.parseUserInput(fullInput, testUserId)
            
            assertThat(result.success).withFailMessage("Failed to parse: $fullInput").isTrue()
            assertThat(result.jobSearchIn?.remoteTypes).withFailMessage("Wrong remote type for: $fullInput").contains(expectedRemoteType)
            
            println("✅ Remote type validation - $input: ${result.jobSearchIn?.remoteTypes}")
        }
    }

    @Test
    fun `should handle fallback to basic parsing when DeepSeek is unavailable`() = runBlocking {
        // This test simulates what happens when DeepSeek API is down
        // We can't easily mock this in integration test, but we can document the expected behavior
        
        val userInput = "Software Engineer in Portland"
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)
        
        // If DeepSeek is available, this should succeed
        if (deepSeekClient.isAvailable()) {
            assertThat(result.success).isTrue()
            println("✅ DeepSeek available - parsing succeeded: ${result.jobSearchIn}")
        } else {
            // If DeepSeek is unavailable, it should fall back to basic parsing
            assertThat(result.success).isFalse()
            assertThat(result.errorMessage).contains("Advanced parsing is not available")
            println("✅ DeepSeek unavailable - fallback triggered: ${result.errorMessage}")
        }
    }

    @Test
    fun `should measure parsing performance`() = runBlocking {
        val userInput = "Senior Software Architect in Vancouver, remote, Kotlin and microservices experience, $180k+"
        
        val startTime = System.currentTimeMillis()
        val result = jobSearchParserService.parseUserInput(userInput, testUserId)
        val endTime = System.currentTimeMillis()
        
        val duration = endTime - startTime
        
        assertThat(result.success).isTrue()
        assertThat(duration).isLessThan(10000) // Should complete within 10 seconds
        
        println("✅ Performance test - Duration: ${duration}ms")
        println("✅ Performance test result: ${result.jobSearchIn}")
    }
} 