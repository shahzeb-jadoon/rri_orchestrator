# RRI Orchestrator - Docker Container
# Use official Python 3.10 slim runtime as base image
FROM python:3.10-slim

# Set working directory in container
WORKDIR /app

# Install system dependencies (if needed for any packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire application code
COPY . .

# Create database directory for persistence
RUN mkdir -p /app/database

# Expose Streamlit default port
EXPOSE 8501

# Health check - ensure app stays running
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run Streamlit application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--logger.level=info"]
