FROM chromedp/headless-shell:latest

# Install Python and venv tools
RUN apt-get update && apt-get install -y python3 python3-pip python3-venv

# Set working directory
WORKDIR /app

# Create and activate virtual environment
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Copy requirements and install within virtualenv
COPY requirements.txt requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the monitor script
COPY monitor.py monitor.py

# Run the monitor
CMD ["python", "monitor.py"]