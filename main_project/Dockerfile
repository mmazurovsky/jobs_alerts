FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy shared package and install it first
COPY shared/ ./shared/
RUN pip install --no-cache-dir -e ./shared

# Copy project requirements and install dependencies
COPY main_project/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main_project/app/ ./app/

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8001

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"] 