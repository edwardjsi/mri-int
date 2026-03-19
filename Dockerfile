FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (root + api)
COPY requirements.txt ./requirements.txt
COPY api/requirements.txt ./api-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r api-requirements.txt

# Copy source code
COPY src/ ./src/
COPY api/ ./api/
COPY scripts/ ./scripts/

# Expose the API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Run FastAPI via uvicorn
#CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
