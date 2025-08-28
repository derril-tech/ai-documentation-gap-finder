# Export Worker Dockerfile

FROM python:3.11-slim

# Install system dependencies for Git and PDF generation
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Create workspace directory
RUN mkdir -p /workspace

# Set environment variables
ENV PYTHONPATH=/app
ENV EXPORT_WORKSPACE_DIR=/workspace

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; from main import ExportWorker; print('Worker can be imported')" || exit 1

# Run the worker
CMD ["python", "main.py"]
