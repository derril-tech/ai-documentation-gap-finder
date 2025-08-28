# Scan Docs Worker Configuration

import os
from pathlib import Path

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"

# NATS configuration
NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")

# Worker configuration
WORKER_CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "20"))  # Higher for docs
QUEUE_GROUP = os.getenv("QUEUE_GROUP", "scan-docs-workers")

# Scan configuration
DEFAULT_DOC_PATTERNS = [
    "**/*.md",
    "**/*.mdx",
    "**/*.markdown"
]

EXTRACT_CODE_BLOCKS = os.getenv("EXTRACT_CODE_BLOCKS", "true").lower() == "true"
BUILD_LINK_GRAPH = os.getenv("BUILD_LINK_GRAPH", "true").lower() == "true"
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))

# Link analysis
CHECK_BROKEN_LINKS = os.getenv("CHECK_BROKEN_LINKS", "true").lower() == "true"
FOLLOW_EXTERNAL_LINKS = os.getenv("FOLLOW_EXTERNAL_LINKS", "false").lower() == "true"

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Monitoring configuration
SENTRY_DSN = os.getenv("SENTRY_DSN")
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
