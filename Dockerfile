# Dockerfile
FROM python:3.11-slim

# Install Playwright system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libgtk-3-0 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install --with-deps chromium

# Copy server source
COPY server/ ./server/

# Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/client
COPY client/package*.json ./
RUN npm ci
COPY client/ ./
RUN npm run build

# Copy built frontend to server's static directory
COPY --from=frontend-builder /app/client/dist /app/server/static
COPY --from=frontend-builder /app/client/dist /app/server/app/static

# Copy uvicorn/gunicorn config
COPY server/gunicorn_conf.py /app/server/gunicorn_conf.py

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "server.app.main:app", "--host", "0.0.0.0", "--port", "8000"]