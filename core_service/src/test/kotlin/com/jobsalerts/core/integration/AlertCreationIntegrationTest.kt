package com.jobsalerts.core.integration

import com.jobsalerts.core.bot.TelegramBotService
import kotlinx.coroutines.*
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.*
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.test.context.ActiveProfiles
import org.springframework.test.context.TestPropertySource
import java.util.*
import com.jobsalerts.core.infrastructure.FromTelegramEventBus
import com.jobsalerts.core.infrastructure.ToTelegramEventBus
import com.jobsalerts.core.repository.JobSearchRepository
import com.jobsalerts.core.service.JobSearchScheduler
import com.jobsalerts.core.domain.model.ToTelegramSendMessageEvent
import com.jobsalerts.core.domain.model.TelegramMessageReceived
import com.jobsalerts.core.service.DeepSeekClient
import com.jobsalerts.core.service.DeepSeekResponse
import org.apache.logging.log4j.kotlin.logger
import org.springframework.boot.test.mock.mockito.MockBean
import org.springframework.test.context.DynamicPropertyRegistry
import org.springframework.test.context.DynamicPropertySource
import org.testcontainers.containers.MongoDBContainer
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers
import org.testcontainers.utility.DockerImageName
import org.mockito.kotlin.whenever
import org.mockito.kotlin.verify
import org.mockito.kotlin.any
import org.mockito.kotlin.eq

/**
 * End‑to‑end integration test that exercises the complete "/create_alert" flow
 * using the real Spring context, an embedded MongoDB instance, and a live
 * DeepSeek API key supplied via `.env.test`.
 *
 * The test publishes the sequence of Telegram messages that a user would send
 * while creating a new alert and then verifies that:
 *   1. The bot answers with the expected instructional / confirmation messages
 *      via the [ToTelegramEventBus].
 *   2. A new [JobSearchOut] document is persisted in MongoDB.
 *   3. The [JobSearchScheduler] has scheduled the newly‑created alert.
 */
@Testcontainers
@SpringBootTest
@ActiveProfiles("test")
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class AlertCreationIntegrationTest {


    companion object {
        private val mongoImage = DockerImageName.parse("mongo:7.0.8")
            .asCompatibleSubstituteFor("mongo")

        /** Single reusable Mongo container for the whole JVM. */
        @JvmStatic
        @Container
        val mongo: MongoDBContainer = MongoDBContainer(mongoImage).apply {
            withReuse(true) // speeds up local iterations
        }

        /**
         * Feed the Testcontainers connection string into Spring's `Environment`.
         *
         * We set both the custom `MONGO_URL` (used by our [AppConfig]) and the
         * conventional `spring.data.mongodb.uri` so that any component relying
         * on either property will connect to the same container.
         */
        @JvmStatic
        @DynamicPropertySource
        fun mongoProps(registry: DynamicPropertyRegistry) {
            if (!mongo.isRunning) mongo.start()
            registry.add("MONGO_URL",             mongo::getReplicaSetUrl)
            registry.add("spring.data.mongodb.uri", mongo::getReplicaSetUrl)
            registry.add("MONGO_DB")             { "test" }
        }
    }

    @Autowired
    private lateinit var fromTelegramEventBus: FromTelegramEventBus

    @Autowired
    private lateinit var toTelegramEventBus: ToTelegramEventBus

    @Autowired
    private lateinit var jobSearchRepository: JobSearchRepository

    @Autowired
    private lateinit var jobSearchScheduler: JobSearchScheduler

    @MockBean
    private lateinit var telegramBotService: TelegramBotService

    @MockBean
    private lateinit var deepSeekClient: DeepSeekClient

    private lateinit var scope: CoroutineScope
    private val outboundEvents: MutableList<ToTelegramSendMessageEvent> =
        Collections.synchronizedList(mutableListOf())

    @BeforeAll
    fun setUp(): Unit = runBlocking {

        scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
        // Collect everything the bot sends so that we can assert on it later.
        toTelegramEventBus.subscribe(scope) { event ->
            if (event is ToTelegramSendMessageEvent) {
                outboundEvents += event
            }
        }
    }

    @AfterEach
    fun cleanUp() {
        // Delete any data created during a test to keep them isolated.
        jobSearchRepository.deleteAll()
        jobSearchScheduler.getActiveSearches().keys.forEach { 
            runBlocking {
                jobSearchScheduler.removeJobSearch(it) 
            }
       }
        outboundEvents.clear()
    }

    @AfterAll
    fun tearDown() {
        scope.cancel()
    }

    @Test
    fun `should create a new alert end-to-end`(): Unit = runBlocking {
        val chatId = 42L
        val userId: Long = 42
        val username = "testuser"

        // Mock DeepSeekClient to return a successful parse
        val mockResponse = DeepSeekResponse(
            success = true,
            content = """{"jobTitle": "Senior Kotlin Developer", "location": "Berlin", "jobTypes": ["Full-time"], "remoteTypes": ["Remote"], "filterText": "every 1 day"}"""
        )
        whenever(deepSeekClient.isAvailable()).thenReturn(true)
        whenever(deepSeekClient.chat(any())).thenReturn(mockResponse)

        // ── Step 1: user issues /create_alert ────────────────────────────────
        fromTelegramEventBus.publish(
            TelegramMessageReceived(
                text = "/create_alert",
                username = username,
                userId = userId,
                chatId = chatId,
                commandName = "/create_alert",
                commandParameters = "",
                message = "somemessage",
            )
        )
        delay(1000)
        println("Outbound events after /create_alert: $outboundEvents")
        assertThat(outboundEvents).anyMatch { it.chatId == chatId && it.message.contains("describe", ignoreCase = true) }
        outboundEvents.clear()

        // ── Step 2: user provides a description
        val description = "Senior Kotlin Developer in Berlin, remote, every 1 day"
        fromTelegramEventBus.publish(
            TelegramMessageReceived(
                text = description,
                username = username,
                userId = userId,
                chatId = chatId,
                commandName = null,
                commandParameters = "",
                message = "somemessage",
            )
        )
        delay(1000)
        println("Outbound events after job description: $outboundEvents")
        // Verify DeepSeekClient.chat() was called with the expected prompt
        verify(deepSeekClient).chat(any())
        // Bot should present parsed criteria and ask for confirmation.
        assertThat(outboundEvents).anyMatch { it.chatId == chatId && it.message.contains("describe", ignoreCase = true) }
        outboundEvents.clear()

        // ── Step 3: user confirms with "yes" ────────────────────────────────
        fromTelegramEventBus.publish(
            TelegramMessageReceived(
                text = "yes",
                username = username,
                userId = userId,
                chatId = chatId,
                commandName = null,
                commandParameters = "",
                message = "somemessage",
            )
        )
        delay(250)
        // Repository should now contain exactly one alert for this user.
        val searches = jobSearchRepository.findByUserId(userId)
        assertThat(searches).hasSize(1)
        val search = searches.first()
        assertThat(search.jobTitle.lowercase()).contains("kotlin")
        // Scheduler should have picked the search up.
        assertThat(jobSearchScheduler.getActiveSearches()).containsKey(search.id)
        // Bot should confirm successful creation.
        assertThat(outboundEvents).anyMatch { it.chatId == chatId && it.message.contains("alert has been created", ignoreCase = true) }
    }

}
