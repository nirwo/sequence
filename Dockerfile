FROM python:3.9-slim

WORKDIR /app

# Install required utilities
RUN apt-get update && \
    apt-get install -y \
    iputils-ping \
    telnet \
    nmap \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# Use Gunicorn as the production server
CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]
