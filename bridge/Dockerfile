FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for layer caching
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source
COPY rempah_bridge/ ./rempah_bridge/

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "rempah_bridge"]
