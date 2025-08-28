# Clone Worker Configuration

import os
from pathlib import Path

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"

# NATS configuration
NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")

# Workspace configuration
WORKSPACE_DIR = Path(os.getenv("CLONE_WORKSPACE_DIR", "/tmp/ai-docgap/clones"))

# Rate limiting configuration
MAX_ATTEMPTS_PER_DOMAIN = int(os.getenv("MAX_ATTEMPTS_PER_DOMAIN", "3"))
BASE_BACKOFF_SECONDS = int(os.getenv("BASE_BACKOFF_SECONDS", "2"))

# Clone configuration
DEFAULT_CLONE_DEPTH = int(os.getenv("DEFAULT_CLONE_DEPTH", "1"))
MAX_CLONE_TIMEOUT = int(os.getenv("MAX_CLONE_TIMEOUT", "300"))  # 5 minutes

# Worker configuration
WORKER_CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "4"))
QUEUE_GROUP = os.getenv("QUEUE_GROUP", "clone-workers")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Monitoring configuration
SENTRY_DSN = os.getenv("SENTRY_DSN")
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
