# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# ============================================
# Stage 1: Build frontend assets
# ============================================
FROM node:20-slim AS frontend-builder

WORKDIR /app

# Copy package files for dependency installation
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts

# Copy TypeScript, Tailwind, and Vite configuration
COPY tsconfig.json vite.config.ts postcss.config.js tailwind.config.ts ./

# Copy source files
COPY src/web/static/ ./src/web/static/
COPY src/web/templates/ ./src/web/templates/

# Build frontend (TypeScript -> JavaScript, bundled with Vite)
RUN npm run build

# ============================================
# Stage 2: Python application
# ============================================
FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Install system dependencies including PostgreSQL client
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy the application code
COPY run_web.py .
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Copy built frontend assets from builder stage
COPY --from=frontend-builder /app/dist/static/ ./dist/static/

# Create data directory and set permissions
RUN mkdir -p data/logs data/backups && \
    adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/api/health || exit 1

# Run the application
CMD ["python", "run_web.py"]
