FROM python:3.11-slim

# Install Chromium, Chromedriver, and venv tools
RUN apt-get update && \
    apt-get install -y chromium chromium-driver python3-venv && \
    rm -rf /var/lib/apt/lists/*

# Ensure Selenium picks up the right binaries and logs are unbuffered
ENV CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy your script and runner
COPY monitor.py start.sh ./
RUN chmod +x start.sh

# Launch the bash wrapper so stdout is unbuffered
CMD ["./start.sh"]
