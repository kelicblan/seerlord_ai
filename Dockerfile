# Stage 1: Build Frontend
FROM node:18-slim AS frontend-builder
WORKDIR /app/admin

# Copy package files first to leverage cache
COPY admin/package.json admin/package-lock.json* ./

# Install dependencies
# Using strict-ssl false to avoid issues in some network environments, optional
RUN npm config set strict-ssl false
RUN npm install

# Copy source code
COPY admin/ .

# Build frontend
RUN npm run build

# Stage 2: Build Backend & Runtime
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for psycopg and other compiled extensions
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY server/ ./server/
COPY scripts/ ./scripts/
# Copy configuration templates
COPY .env.example ./.env
# Copy MCP config if exists
COPY mcp.json .

# Copy frontend build artifacts to backend static folder
# server/main.py is configured to serve static files from server/static
COPY --from=frontend-builder /app/admin/dist ./server/static

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose the application port
EXPOSE 8000

# Start the application
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
