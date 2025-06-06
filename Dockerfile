# syntax=docker/dockerfile:1
FROM python:3.11-bullseye

# Set environment variables for locale and timezone
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8 \
    TZ=Europe/Berlin \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    ca-certificates \
    tzdata \
    locales \
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
    gconf-service \
    libappindicator1 \
    libnss3-tools \
    v4l2loopback-utils \
    pulseaudio \
    && rm -rf /var/lib/apt/lists/*

# Fonts used by LinkedIn and system mimicking    
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-liberation \
    fonts-dejavu \
    fonts-noto \
    fonts-noto-cjk \
    fonts-ipafont \
    fonts-freefont-ttf \
    fonts-croscore \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -f -v

# Generate locale
RUN locale-gen en_US.UTF-8

# Create non-root user
RUN useradd -ms /bin/bash scraper
USER scraper
WORKDIR /home/scraper/app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers as the non-root user
RUN python -m playwright install

# Copy application code
COPY --chown=scraper:scraper src/ ./src/
COPY --chown=scraper:scraper data/ ./data/
COPY --chown=scraper:scraper logs/ ./logs/
COPY --chown=scraper:scraper tests/ ./tests/

# Set PYTHONPATH for imports
ENV PYTHONPATH=/home/scraper/app

# Entry point
CMD ["python", "src/main.py"]
