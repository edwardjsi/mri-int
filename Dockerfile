# Rebuild trigger - ensures Docker cache invalidation (2026-06-19T14:58:00Z)
# Unified Multi-Stage Dockerfile for MRI Platform (v2.0 Sync)
# Stage 1: Build the React Frontend
FROM node:18-slim as frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
# Frontend rebuild trigger: 2026-05-29T17:30:00Z
COPY frontend/ ./
RUN npm run build

# Stage 2: Build the Python Backend
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./requirements.txt
COPY api/requirements.txt ./api-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r api-requirements.txt
# Explicitly install psycopg2-binary to avoid stale-cache issues
RUN pip install --no-cache-dir psycopg2-binary
# markitdown installed separately to avoid dependency resolution explosion
RUN pip install --no-cache-dir markitdown

# Copy backend source code
# Note: code now lives in engine_core/ (legacy src/ was removed)
COPY engine_core/ ./engine_core/
COPY engine_fundamental/ ./engine_fundamental/
COPY engine_qualitative/ ./engine_qualitative/
COPY engine_perx/ ./engine_perx/
COPY engine_guidance/ ./engine_guidance/
COPY engine_debate/ ./engine_debate/
COPY api/ ./api/
COPY scripts/ ./scripts/

# Copy built frontend from Stage 1 into the api/static directory
COPY --from=frontend-builder /app/frontend/dist/ ./api/static/

# Expose the port (Railway uses $PORT)
EXPOSE 8000

# Run FastAPI via uvicorn
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
