# Job Alerts System

A microservices-based job search alert system that scrapes LinkedIn for job postings and sends notifications via Telegram bot.

## Architecture

The system consists of two main services:

- **LinkedIn Scraper Service**: Scrapes job postings from LinkedIn using Playwright
- **Main Project**: Telegram bot that manages user interactions and job search configurations

## Services

### LinkedIn Scraper Service (`linkedin_scraper_service/`)
- Web scraping service using Playwright
- REST API for job search requests
- Filters and processes job postings
- Returns structured job data

### Main Project (`main_project/`)
- Telegram bot interface
- User session management
- Job search scheduling
- MongoDB database integration
- Natural language command processing (planned)

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.8+
- MongoDB instance
- Telegram Bot Token

### Environment Setup

1. Copy environment template:
```bash
cp .env.example .env
```

2. Configure your environment variables:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
MONGODB_URL=mongodb://localhost:27017
SCRAPER_SERVICE_URL=http://linkedin_scraper_service:8000
DEEPSEEK_API_KEY=your_deepseek_api_key
```

### Running with Docker

Run the entire stack:
```bash
./run_local_stack.sh
```

Or run services individually:
```bash
# LinkedIn scraper service
./run_scraper_local.sh

# Main Telegram bot
./run_main_local.sh
```

### Running Locally (Development)

1. Install dependencies:
```bash
pip install -r main_project/requirements.txt
pip install -r linkedin_scraper_service/requirements.txt
```

2. Start services:
```bash
# Terminal 1 - Scraper service
cd linkedin_scraper_service
python -m app.main

# Terminal 2 - Main bot
cd main_project
python -m app.main
```

## Telegram Bot Commands

- `/start` - Start the bot and see available commands
- `/newRaw <search_params>` - Create a new job search alert
- `/list` - List all your active job searches
- `/delete <search_id>` - Delete a specific job search
- `/oneTimeDeepSearch <search_params>` - Perform immediate job search

### Natural Language Interface (Coming Soon)
The bot will support free-form natural language commands like:
- "Find Python developer jobs in Berlin"
- "Create alerts for remote software engineer positions"
- "Show me my job searches"
- "Delete search abc123"

## Task Management

See [`tasks.md`](tasks.md) for current development tasks and priorities.

## Project Structure

```
jobs_alerts/
├── linkedin_scraper_service/     # Scraping service
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── scraper.py           # LinkedIn scraper logic
│   │   └── llm/                 # LLM integration
│   └── docker-compose.yml
├── main_project/                # Main Telegram bot
│   ├── app/
│   │   ├── main.py              # Application entry point
│   │   ├── bot/                 # Telegram bot logic
│   │   ├── core/                # Core business logic
│   │   ├── schedulers/          # Job scheduling
│   │   └── llm/                 # DeepSeek integration
│   └── docker-compose.yml
├── shared/                      # Shared utilities
└── tasks.md                     # Development tasks
```

## Development

### Adding New Features

1. Check [`tasks.md`](tasks.md) for current priorities
2. Create feature branch: `git checkout -b feature/your-feature`
3. Implement changes following existing patterns
4. Update task status in `tasks.md`
5. Test thoroughly
6. Submit pull request

### Testing

Run tests for individual services:
```bash
# Scraper service tests
cd linkedin_scraper_service
python -m pytest

# Main project tests
cd main_project
python -m pytest tests/
```

## Deployment

The system is designed for containerized deployment. Use the provided Docker configurations and deployment scripts.

For production deployment:
1. Configure production environment variables
2. Use `docker-compose.yml` files (without override files)
3. Ensure network connectivity between services
4. Set up monitoring and logging

## Contributing

1. Follow Python coding standards
2. Update [`tasks.md`](tasks.md) with progress
3. Add tests for new functionality
4. Update documentation as needed

## License

This project is for educational and personal use. 