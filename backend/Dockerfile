FROM python:3.11-slim AS base

# System deps for lxml, psycopg2, Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc libxml2-dev libxslt1-dev zlib1g-dev libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Non-root user for security
RUN useradd -m -u 1000 utap && chown -R utap:utap /app
USER utap

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production

EXPOSE 8000

# Run Alembic migrations then start Uvicorn
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers --forwarded-allow-ips='*'"]
