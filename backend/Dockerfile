FROM python:3.12-slim

# System deps for asyncpg / spaCy
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

# Download spaCy model
RUN python -m spacy download en_core_web_lg

# Copy source
COPY . .

# Non-root user
RUN useradd -m -u 1001 beacon
USER beacon

EXPOSE 8000

CMD ["uvicorn", "beacon.main:app", "--host", "0.0.0.0", "--port", "8000"]
