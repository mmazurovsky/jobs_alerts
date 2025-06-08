FROM python:3.11-slim

# Set environment variables for locale and timezone
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8 \
    TZ=Europe/Berlin \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    locales \
    curl \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Generate locale
RUN locale-gen en_US.UTF-8

# Create non-root user
RUN useradd -ms /bin/bash app

# Set work directory
WORKDIR /app

# Copy shared package and install it first
COPY shared/ ./shared/
RUN pip install --no-cache-dir -e ./shared

# Copy project requirements and install dependencies
COPY main_project/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main_project/app/ ./app/

# Change ownership before installing as app
RUN chown -R app:app /app

ENV PYTHONPATH=/app

# Switch to non-root user BEFORE install
USER app

# Expose port
EXPOSE 8001

# Run the application
CMD ["uvicorn", "main_project.app.main:app", "--host", "0.0.0.0", "--port", "8001", "--timeout-keep-alive", "500", "--timeout-graceful-shutdown", "500"] 