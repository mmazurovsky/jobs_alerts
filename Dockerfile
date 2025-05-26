# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Install system dependencies for Playwright/Chromium
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    libxss1 \
    libappindicator3-1 \
    libatspi2.0-0 \
    libwayland-client0 \
    libwayland-cursor0 \
    libwayland-egl1 \
    libxkbcommon0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcurl4 \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium)
RUN python -m playwright install --with-deps chromium

# Copy application code
COPY src/ ./src/
COPY data/ ./data/
COPY logs/ ./logs/
COPY tests/ ./tests/

# Expose any ports if needed (uncomment if running FastAPI server)
# EXPOSE 8000

# Set PYTHONPATH
ENV PYTHONPATH=/app

# Default command
CMD ["python", "src/main.py"] 