FROM python:3.9-slim

WORKDIR /app

# Install required utilities and create non-root user
RUN apt-get update && \
    apt-get install -y \
    iputils-ping \
    telnet \
    nmap \
    && rm -rf /var/lib/apt/lists/* && \
    # Create non-root user
    useradd -m -U appuser && \
    # Give ping permissions to non-root user
    chmod u+s /bin/ping && \
    # Set proper permissions
    chown -R appuser:appuser /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

EXPOSE 5000

# Use Gunicorn as the production server
CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]
