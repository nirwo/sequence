FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# Use Gunicorn as the production server
CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]
