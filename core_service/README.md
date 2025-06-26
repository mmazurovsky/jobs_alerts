# Jobs Alerts Core Service

This is a Kotlin/Spring Boot implementation of the Jobs Alerts main project, providing the same functionality as the Python version but with Spring Boot 3, Kotlin, and Java 21.

## Features

- **Job Search Management**: Create, list, and delete job searches
- **Automated Scheduling**: Uses Quartz scheduler for periodic job searches
- **Telegram Bot Integration**: Basic bot functionality for notifications
- **MongoDB Integration**: Stores job searches and sent jobs
- **Scraper Service Integration**: Communicates with the LinkedIn scraper service
- **Event-Driven Architecture**: Uses RxKotlin for event streaming

## Technology Stack

- **Language**: Kotlin
- **Framework**: Spring Boot 3
- **Java Version**: 21
- **Build Tool**: Gradle
- **Database**: MongoDB
- **Scheduler**: Quartz
- **HTTP Client**: Ktor
- **Telegram Bot**: kotlin-telegram-bot
- **Reactive**: RxKotlin

## Prerequisites

- Java 21
- MongoDB
- Docker (optional)
- Environment variables configured

## Configuration

Create a `.env` file in the parent directory with:

```env
MONGO_URL=mongodb://localhost:27017/jobs_alerts
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
ADMIN_USER_ID=your_admin_telegram_id
DEEPSEEK_API_KEY=your_deepseek_api_key  # Optional
CALLBACK_URL=http://localhost:8080
SCRAPER_SERVICE_URL=http://localhost:8000
LOG_LEVEL=INFO
```

## Running Locally

### Using Gradle

```bash
./gradlew bootRun
```

### Using Docker

```bash
./deploy.sh
```

## API Endpoints

### `POST /job_results_callback`
Webhook endpoint for receiving job search results from the scraper service.

**Request Body:**
```json
{
  "job_search_id": "string",
  "user_id": 123,
  "jobs": [
    {
      "title": "string",
      "company": "string", 
      "location": "string",
      "link": "string",
      "created_ago": "string",
      "techstack": ["string"],
      "compatibility_score": 85,
      "filter_reason": "string"
    }
  ]
}
```

**Response:**
```json
{
  "status": "received"
}
```

### Actuator Endpoints

- `GET /actuator/health` - Comprehensive health check (MongoDB, Scraper Service)
- `GET /actuator/health/liveness` - Kubernetes liveness probe
- `GET /actuator/health/readiness` - Kubernetes readiness probe
- `GET /actuator/info` - Application info
- `GET /actuator/metrics` - Application metrics
- `GET /actuator/env` - Environment properties
- `GET /actuator/beans` - Spring beans
- `GET /actuator/mappings` - Request mappings

## Project Structure

```
core_service/
├── src/
│   └── main/
│       ├── kotlin/com/jobsalerts/core/
│       │   ├── bot/           # Telegram bot service
│       │   ├── config/        # Configuration classes
│       │   ├── controller/    # REST controllers
│       │   ├── domain/model/  # Domain models
│       │   ├── repository/    # MongoDB repositories
│       │   └── service/       # Business logic services
│       └── resources/
│           └── application.yml # Application configuration
├── build.gradle.kts           # Build configuration
├── Dockerfile
├── docker-compose.yml
└── deploy.sh
```

## Development

The service provides the same functionality as the Python version:

1. **Job Search Management**: Create and manage job searches with scheduling
2. **Telegram Notifications**: Send job alerts to users via Telegram
3. **Scraper Integration**: Trigger job searches on the scraper service
4. **Event Streaming**: Publish events for Telegram message sending

## Differences from Python Version

- Uses Spring Boot's dependency injection instead of manual container
- Quartz scheduler instead of APScheduler
- Spring Data MongoDB instead of Motor/PyMongo
- Ktor HTTP client instead of httpx
- kotlin-telegram-bot instead of python-telegram-bot
- RxKotlin for reactive streams instead of Python's rx

## Building for Production

```bash
./gradlew build
```

The JAR file will be in `build/libs/`

## Docker Deployment

The service includes Docker support:

```bash
docker-compose up -d
```

This will build and run the service with all required environment variables. 