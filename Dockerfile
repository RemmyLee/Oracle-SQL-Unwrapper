# Multi-stage Dockerfile for PL/SQL Workbench
# Stage 1: Build stage for dependencies
FROM python:3.9-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    wget \
    unzip \
    libaio1 \
    && rm -rf /var/lib/apt/lists/*

# Install Oracle Instant Client (optional - comment out if not needed)
RUN mkdir -p /opt/oracle && \
    cd /opt/oracle && \
    wget https://download.oracle.com/otn_software/linux/instantclient/1919000/instantclient-basic-linux.x64-19.19.0.0.0dbru.zip && \
    unzip instantclient-basic-linux.x64-19.19.0.0.0dbru.zip && \
    rm instantclient-basic-linux.x64-19.19.0.0.0dbru.zip && \
    cd instantclient_19_19 && \
    echo /opt/oracle/instantclient_19_19 > /etc/ld.so.conf.d/oracle-instantclient.conf && \
    ldconfig

# Create virtual environment
RUN python -m venv /opt/venv

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Production stage
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libaio1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Oracle Instant Client from builder (optional)
COPY --from=builder /opt/oracle /opt/oracle
RUN echo /opt/oracle/instantclient_19_19 > /etc/ld.so.conf.d/oracle-instantclient.conf && \
    ldconfig

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_ENV=production \
    ORACLE_HOME=/opt/oracle/instantclient_19_19 \
    LD_LIBRARY_PATH=/opt/oracle/instantclient_19_19

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/logs /app/uploads && \
    chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run Gunicorn
CMD ["gunicorn", \
    "--workers", "4", \
    "--worker-class", "sync", \
    "--threads", "2", \
    "--bind", "0.0.0.0:8000", \
    "--timeout", "300", \
    "--access-logfile", "-", \
    "--error-logfile", "-", \
    "--log-level", "info", \
    "backend.app:create_app('production')"]
