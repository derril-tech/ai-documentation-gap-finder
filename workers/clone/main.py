#!/usr/bin/env python3
"""
AI Documentation Gap Finder - Clone Worker

Handles repository cloning with shallow/sparse checkout, LFS support,
rate limiting, and backoff strategies.

Features:
- Shallow cloning with depth=1 by default
- Sparse checkout for monorepos
- Git LFS support for images/screens
- Per-project queuing
- Rate limiting with exponential backoff
- Error handling and retries
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import aiofiles
import httpx
from nats.aio.client import Client as NATS
from nats.aio.errors import ErrTimeout
import redis.asyncio as redis
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@dataclass
class CloneRequest:
    """Clone request data structure"""
    project_id: str
    repo_url: str
    branch: str = "main"
    depth: int = 1
    sparse_paths: Optional[List[str]] = None
    include_lfs: bool = True
    priority: int = 0
    request_id: str = ""


@dataclass
class CloneResult:
    """Clone result data structure"""
    project_id: str
    repo_url: str
    local_path: str
    success: bool
    error_message: Optional[str] = None
    commit_hash: Optional[str] = None
    clone_duration: float = 0.0
    request_id: str = ""


class RateLimiter:
    """Rate limiter with exponential backoff"""

    def __init__(self, redis_client: redis.Redis, max_attempts: int = 3):
        self.redis = redis_client
        self.max_attempts = max_attempts

    async def check_rate_limit(self, domain: str) -> Tuple[bool, float]:
        """Check if domain is rate limited. Returns (allowed, wait_time)"""
        key = f"ratelimit:{domain}"
        attempts = await self.redis.get(key)

        if attempts and int(attempts) >= self.max_attempts:
            # Calculate backoff time (exponential)
            wait_time = 2 ** (int(attempts) - self.max_attempts)
            return False, wait_time

        return True, 0.0

    async def record_attempt(self, domain: str, success: bool):
        """Record an attempt for rate limiting"""
        key = f"ratelimit:{domain}"

        if success:
            # Reset on success
            await self.redis.delete(key)
        else:
            # Increment failure count with expiry
            await self.redis.incr(key)
            await self.redis.expire(key, 3600)  # 1 hour expiry


class GitCloneManager:
    """Manages Git cloning operations"""

    def __init__(self, workspace_dir: Path, rate_limiter: RateLimiter):
        self.workspace_dir = workspace_dir
        self.rate_limiter = rate_limiter
        self.workspace_dir.mkdir(exist_ok=True)

    def get_local_path(self, project_id: str, repo_url: str) -> Path:
        """Generate local path for repository"""
        domain = urlparse(repo_url).netloc
        repo_name = Path(repo_url).stem
        return self.workspace_dir / domain / project_id / repo_name

    async def clone_repository(self, request: CloneRequest) -> CloneResult:
        """Clone a repository with all optimizations"""
        start_time = time.time()
        local_path = self.get_local_path(request.project_id, request.repo_url)

        try:
            # Check rate limiting
            domain = urlparse(request.repo_url).netloc
            allowed, wait_time = await self.rate_limiter.check_rate_limit(domain)

            if not allowed:
                logger.warning("Rate limited", domain=domain, wait_time=wait_time)
                await asyncio.sleep(wait_time)
                # Re-check after waiting
                allowed, _ = await self.rate_limiter.check_rate_limit(domain)
                if not allowed:
                    raise Exception(f"Rate limited for domain {domain}")

            # Clean up existing directory if it exists
            if local_path.exists():
                shutil.rmtree(local_path)

            # Create parent directories
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # Perform the clone
            await self._perform_clone(request, local_path)

            # Get commit hash
            commit_hash = await self._get_commit_hash(local_path)

            # Record success
            await self.rate_limiter.record_attempt(domain, True)

            duration = time.time() - start_time
            logger.info("Clone successful",
                       project_id=request.project_id,
                       repo_url=request.repo_url,
                       local_path=str(local_path),
                       duration=duration,
                       commit_hash=commit_hash)

            return CloneResult(
                project_id=request.project_id,
                repo_url=request.repo_url,
                local_path=str(local_path),
                success=True,
                commit_hash=commit_hash,
                clone_duration=duration,
                request_id=request.request_id
            )

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)

            # Record failure for rate limiting
            domain = urlparse(request.repo_url).netloc
            await self.rate_limiter.record_attempt(domain, False)

            logger.error("Clone failed",
                        project_id=request.project_id,
                        repo_url=request.repo_url,
                        error=error_msg,
                        duration=duration)

            return CloneResult(
                project_id=request.project_id,
                repo_url=request.repo_url,
                local_path=str(local_path),
                success=False,
                error_message=error_msg,
                clone_duration=duration,
                request_id=request.request_id
            )

    async def _perform_clone(self, request: CloneRequest, local_path: Path):
        """Perform the actual git clone operation"""
        cmd = ["git", "clone"]

        # Add shallow clone
        if request.depth > 0:
            cmd.extend(["--depth", str(request.depth)])

        # Add branch
        cmd.extend(["--branch", request.branch])

        # Add sparse checkout if specified
        if request.sparse_paths:
            cmd.append("--sparse")
            # We'll configure sparse checkout after clone

        # Add repository URL and local path
        cmd.extend([request.repo_url, str(local_path)])

        logger.debug("Executing git clone", command=cmd)

        # Run the clone command
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode().strip() or stdout.decode().strip()
            raise Exception(f"Git clone failed: {error_msg}")

        # Configure sparse checkout if needed
        if request.sparse_paths:
            await self._configure_sparse_checkout(local_path, request.sparse_paths)

        # Handle LFS if requested
        if request.include_lfs:
            await self._handle_lfs(local_path)

    async def _configure_sparse_checkout(self, repo_path: Path, sparse_paths: List[str]):
        """Configure sparse checkout for the repository"""
        try:
            # Initialize sparse checkout
            await self._run_git_command(repo_path, ["sparse-checkout", "init", "--cone"])

            # Set the sparse paths
            await self._run_git_command(repo_path, ["sparse-checkout", "set"] + sparse_paths)

        except Exception as e:
            logger.warning("Failed to configure sparse checkout", error=str(e))

    async def _handle_lfs(self, repo_path: Path):
        """Handle Git LFS operations"""
        try:
            # Check if LFS is installed
            process = await asyncio.create_subprocess_exec(
                "git", "lfs", "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=repo_path
            )
            await process.communicate()

            if process.returncode == 0:
                # Pull LFS files
                await self._run_git_command(repo_path, ["lfs", "pull"])
                logger.debug("LFS pull completed", repo_path=str(repo_path))
            else:
                logger.debug("Git LFS not available, skipping LFS operations")

        except Exception as e:
            logger.warning("LFS operations failed", error=str(e))

    async def _run_git_command(self, repo_path: Path, args: List[str]) -> Tuple[str, str]:
        """Run a git command in the repository"""
        cmd = ["git"] + args
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=repo_path
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode().strip()
            raise Exception(f"Git command failed: {' '.join(cmd)} - {error_msg}")

        return stdout.decode().strip(), stderr.decode().strip()

    async def _get_commit_hash(self, repo_path: Path) -> Optional[str]:
        """Get the current commit hash"""
        try:
            stdout, _ = await self._run_git_command(repo_path, ["rev-parse", "HEAD"])
            return stdout.strip()
        except Exception:
            return None


class CloneWorker:
    """Main clone worker class"""

    def __init__(self, config: Dict):
        self.config = config
        self.workspace_dir = Path(config.get("workspace_dir", "/tmp/ai-docgap/clones"))
        self.redis_client = None
        self.nats_client = None
        self.rate_limiter = None
        self.clone_manager = None

    async def initialize(self):
        """Initialize connections and components"""
        # Initialize Redis
        self.redis_client = redis.Redis(
            host=self.config.get("redis_host", "localhost"),
            port=self.config.get("redis_port", 6379),
            decode_responses=True
        )

        # Initialize NATS
        self.nats_client = NATS()
        await self.nats_client.connect(
            self.config.get("nats_url", "nats://localhost:4222")
        )

        # Initialize rate limiter
        self.rate_limiter = RateLimiter(self.redis_client)

        # Initialize clone manager
        self.clone_manager = GitCloneManager(self.workspace_dir, self.rate_limiter)

        logger.info("Clone worker initialized",
                   workspace_dir=str(self.workspace_dir))

    async def run(self):
        """Main worker loop"""
        await self.initialize()

        # Subscribe to clone requests
        subject = "repo.clone"
        queue_group = "clone-workers"

        logger.info("Subscribing to clone requests", subject=subject, queue=queue_group)

        async def message_handler(msg):
            await self.handle_clone_request(msg)

        await self.nats_client.subscribe(
            subject,
            queue=queue_group,
            cb=message_handler
        )

        # Keep the worker running
        while True:
            await asyncio.sleep(1)

    async def handle_clone_request(self, msg):
        """Handle incoming clone request"""
        try:
            # Parse the request
            data = json.loads(msg.data.decode())
            request = CloneRequest(**data)

            logger.info("Processing clone request",
                       project_id=request.project_id,
                       repo_url=request.repo_url,
                       request_id=request.request_id)

            # Perform the clone
            result = await self.clone_manager.clone_repository(request)

            # Publish result
            result_data = {
                "project_id": result.project_id,
                "repo_url": result.repo_url,
                "local_path": result.local_path,
                "success": result.success,
                "error_message": result.error_message,
                "commit_hash": result.commit_hash,
                "clone_duration": result.clone_duration,
                "request_id": result.request_id,
                "timestamp": time.time()
            }

            result_subject = "repo.clone.result"
            await self.nats_client.publish(result_subject, json.dumps(result_data).encode())

            # Acknowledge the message
            await msg.ack()

            logger.info("Clone request processed",
                       project_id=request.project_id,
                       success=result.success)

        except Exception as e:
            logger.error("Failed to process clone request", error=str(e))
            # In a production system, you might want to handle retries here

    async def shutdown(self):
        """Clean shutdown"""
        if self.nats_client:
            await self.nats_client.close()
        if self.redis_client:
            await self.redis_client.close()


async def main():
    """Main entry point"""
    # Load configuration
    config = {
        "redis_host": os.getenv("REDIS_HOST", "localhost"),
        "redis_port": int(os.getenv("REDIS_PORT", "6379")),
        "nats_url": os.getenv("NATS_URL", "nats://localhost:4222"),
        "workspace_dir": os.getenv("CLONE_WORKSPACE_DIR", "/tmp/ai-docgap/clones"),
    }

    # Initialize worker
    worker = CloneWorker(config)

    # Handle shutdown gracefully
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        asyncio.create_task(worker.shutdown())
        sys.exit(0)

    # In production, you would set up proper signal handlers
    # signal.signal(signal.SIGTERM, signal_handler)
    # signal.signal(signal.SIGINT, signal_handler)

    try:
        await worker.run()
    except Exception as e:
        logger.error("Worker failed", error=str(e))
        await worker.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
