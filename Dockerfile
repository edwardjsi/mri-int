# Unified Multi-Stage Dockerfile for MRI Platform
# Stage 1: Build the React Frontend
FROM node:18-slim as frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
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

# Copy backend source code
COPY src/ ./src/
COPY api/ ./api/
COPY scripts/ ./scripts/

# Copy built frontend from Stage 1 into the api/static directory
COPY --from=frontend-builder /app/frontend/dist/ ./api/static/

# Expose the port (Railway uses $PORT)
EXPOSE 8000

# Run FastAPI via uvicorn
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
