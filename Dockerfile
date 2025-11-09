FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./

RUN pip install --no-cache-dir \
    psycopg2-binary>=2.9.11 \
    python-dotenv>=1.2.1 \
    python-telegram-bot>=22.5 \
    schedule>=1.2.2 \
    telethon>=1.41.2

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
