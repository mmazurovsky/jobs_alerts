# syntax=docker/dockerfile:1
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

COPY shared/ ./shared/
COPY linkedin_scraper_service/requirements.txt ./
COPY linkedin_scraper_service/app/ ./app/

RUN pip install --no-cache-dir -e ./shared && \
    pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app

USER pwuser

EXPOSE 8002

CMD ["uvicorn", "linkedin_scraper_service.app.main:app", "--host", "0.0.0.0", "--port", "8002", "--timeout-keep-alive", "500", "--timeout-graceful-shutdown", "500"]