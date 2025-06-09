# syntax=docker/dockerfile:1
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

# Copy only the linkedin_scraper_service and shared directories
COPY linkedin_scraper_service/ ./linkedin_scraper_service/
COPY shared/ ./shared/

RUN pip install --no-cache-dir -r linkedin_scraper_service/requirements.txt

ENV PYTHONPATH=/app

CMD ["uvicorn", "linkedin_scraper_service.app.main:app", "--host", "0.0.0.0", "--port", "8002", "--timeout-keep-alive", "300", "--timeout-graceful-shutdown", "300"]