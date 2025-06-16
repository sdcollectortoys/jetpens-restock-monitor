FROM chromedp/headless-shell:latest

# Use Python base on top of headless-shell
RUN apt-get update && apt-get install -y python3 python3-pip

# Set working directory
WORKDIR /app

# Copy in Python code and install dependencies
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY monitor.py monitor.py

CMD ["python3", "monitor.py"]