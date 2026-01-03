FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./

# Install Python dependencies (Pyrogram instead of Telethon)
RUN pip install --no-cache-dir \
    psycopg2-binary>=2.9.11 \
    python-dotenv>=1.2.1 \
    python-telegram-bot>=22.5 \
    schedule>=1.2.2 \
    pyrogram>=2.0.106 \
    tgcrypto>=1.2.5

COPY . .

ENV PYTHONUNBUFFERED=1

# Default command (overridden by docker-compose)
CMD ["python", "main_seller.py"]