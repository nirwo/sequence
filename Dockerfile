FROM python:3.9-slim

WORKDIR /app

# Install system dependencies and create non-root user
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    iputils-ping \
    curl \
    && rm -rf /var/lib/apt/lists/* && \
    useradd -m appuser

# Copy application files
COPY . .

# Set ownership before switching to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=development

# Run the application
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]
