#!/usr/bin/env python3
"""
AI Documentation Gap Finder - Documentation Scanner Worker

Parses Markdown/MDX documentation files to extract structure, links, and code blocks.
Supports heading hierarchies, anchor generation, link graphs, and embedded code snippets.

Features:
- MD/MDX parsing with remark/rehype-like functionality
- Heading hierarchy and anchor extraction
- Link graph analysis
- Code block extraction and language detection
- Frontmatter parsing
- Async processing with NATS/Redis
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from urllib.parse import urlparse

import aiofiles
import httpx
from nats.aio.client import Client as NATS
from nats.aio.errors import ErrTimeout
import redis.asyncio as redis
import structlog
import yaml
from bs4 import BeautifulSoup

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
class DocHeading:
    """Represents a heading in documentation"""
    level: int
    text: str
    anchor: str
    line_number: int


@dataclass
class DocLink:
    """Represents a link in documentation"""
    text: str
    url: str
    line_number: int
    is_external: bool = False


@dataclass
class CodeBlock:
    """Represents a code block in documentation"""
    language: str
    code: str
    line_number: int


@dataclass
class DocEntity:
    """Represents a documentation entity"""
    id: str
    project_id: str
    path: str
    title: Optional[str]
    headings: List[DocHeading]
    links: List[DocLink]
    code_blocks: List[CodeBlock]
    frontmatter: Optional[Dict[str, Any]]
    last_commit: Optional[str]
    last_updated: Optional[float]
    word_count: int = 0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class DocScanRequest:
    """Documentation scan request"""
    project_id: str
    repo_path: str
    doc_patterns: List[str] = None
    include_patterns: List[str] = None
    exclude_patterns: List[str] = None
    extract_code_blocks: bool = True
    build_link_graph: bool = True
    request_id: str = ""


@dataclass
class DocScanResult:
    """Documentation scan result"""
    project_id: str
    repo_path: str
    docs: List[DocEntity]
    success: bool
    error_message: Optional[str] = None
    scan_duration: float = 0.0
    files_processed: int = 0
    request_id: str = ""


class MarkdownParser:
    """Markdown/MDX parser with comprehensive feature extraction"""

    def __init__(self):
        self.extensions = {".md", ".mdx", ".markdown"}

        # Patterns for parsing
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        self.link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        self.code_block_pattern = re.compile(r'```(\w+)?\n(.*?)\n```', re.DOTALL)
        self.frontmatter_pattern = re.compile(r'^---\n(.*?)\n---', re.DOTALL | re.MULTILINE)

        # Inline code pattern
        self.inline_code_pattern = re.compile(r'`([^`]+)`')

    def can_parse(self, file_path: Path) -> bool:
        """Check if file can be parsed"""
        return file_path.suffix.lower() in self.extensions

    async def parse_file(self, file_path: Path) -> Optional[DocEntity]:
        """Parse a documentation file"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()

            # Parse frontmatter
            frontmatter = self._parse_frontmatter(content)

            # Remove frontmatter from content for processing
            content_without_frontmatter = self.frontmatter_pattern.sub('', content, count=1)

            # Parse headings
            headings = self._parse_headings(content_without_frontmatter)

            # Parse links
            links = self._parse_links(content_without_frontmatter)

            # Parse code blocks
            code_blocks = self._parse_code_blocks(content_without_frontmatter)

            # Extract title from first heading or frontmatter
            title = self._extract_title(frontmatter, headings)

            # Generate ID
            doc_id = f"{file_path}"

            # Word count
            word_count = len(content_without_frontmatter.split())

            return DocEntity(
                id=doc_id,
                project_id="",  # Will be set by caller
                path=str(file_path),
                title=title,
                headings=headings,
                links=links,
                code_blocks=code_blocks,
                frontmatter=frontmatter,
                word_count=word_count
            )

        except Exception as e:
            logger.error("Failed to parse documentation file",
                        file=str(file_path),
                        error=str(e))
            return None

    def _parse_frontmatter(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse YAML frontmatter"""
        match = self.frontmatter_pattern.search(content)
        if match:
            try:
                return yaml.safe_load(match.group(1))
            except yaml.YAMLError as e:
                logger.warning("Failed to parse frontmatter", error=str(e))
        return None

    def _parse_headings(self, content: str) -> List[DocHeading]:
        """Parse headings and generate anchors"""
        headings = []

        for match in self.heading_pattern.finditer(content):
            level = len(match.group(1))
            text = match.group(2).strip()

            # Generate anchor (GitHub-style)
            anchor = self._generate_anchor(text)

            # Get line number
            line_number = content[:match.start()].count('\n') + 1

            headings.append(DocHeading(
                level=level,
                text=text,
                anchor=anchor,
                line_number=line_number
            ))

        return headings

    def _parse_links(self, content: str) -> List[DocLink]:
        """Parse links in the document"""
        links = []

        for match in self.link_pattern.finditer(content):
            text = match.group(1)
            url = match.group(2)

            # Get line number
            line_number = content[:match.start()].count('\n') + 1

            # Check if external
            is_external = self._is_external_link(url)

            links.append(DocLink(
                text=text,
                url=url,
                line_number=line_number,
                is_external=is_external
            ))

        return links

    def _parse_code_blocks(self, content: str) -> List[CodeBlock]:
        """Parse code blocks"""
        code_blocks = []

        for match in self.code_block_pattern.finditer(content):
            language = match.group(1) or ""
            code = match.group(2)

            # Get line number
            line_number = content[:match.start()].count('\n') + 1

            code_blocks.append(CodeBlock(
                language=language.lower(),
                code=code,
                line_number=line_number
            ))

        return code_blocks

    def _generate_anchor(self, text: str) -> str:
        """Generate GitHub-style anchor"""
        # Remove punctuation and convert to lowercase
        anchor = re.sub(r'[^\w\s-]', '', text).lower()
        # Replace spaces and underscores with hyphens
        anchor = re.sub(r'[\s_]+', '-', anchor)
        # Remove multiple consecutive hyphens
        anchor = re.sub(r'-+', '-', anchor)
        # Remove leading/trailing hyphens
        return anchor.strip('-')

    def _is_external_link(self, url: str) -> bool:
        """Check if link is external"""
        if url.startswith(('http://', 'https://', 'mailto:', 'tel:')):
            return True

        # Check if it's an absolute path
        return url.startswith('/')

    def _extract_title(self, frontmatter: Optional[Dict], headings: List[DocHeading]) -> Optional[str]:
        """Extract title from frontmatter or first heading"""
        if frontmatter and 'title' in frontmatter:
            return frontmatter['title']

        if headings:
            return headings[0].text

        return None


class LinkGraphAnalyzer:
    """Analyzes link relationships between documents"""

    def __init__(self):
        self.link_graph: Dict[str, Set[str]] = {}

    def add_document(self, doc: DocEntity):
        """Add document to link graph"""
        doc_path = doc.path

        if doc_path not in self.link_graph:
            self.link_graph[doc_path] = set()

        # Add outgoing links
        for link in doc.links:
            if not link.is_external and not link.url.startswith('/'):
                # Convert relative link to absolute path
                linked_path = self._resolve_relative_link(doc_path, link.url)
                if linked_path:
                    self.link_graph[doc_path].add(linked_path)

    def _resolve_relative_link(self, from_path: str, link_url: str) -> Optional[str]:
        """Resolve relative link to absolute path"""
        if link_url.startswith('./'):
            link_url = link_url[2:]
        elif link_url.startswith('../'):
            # Handle parent directory traversal
            pass

        try:
            from_dir = Path(from_path).parent
            resolved = (from_dir / link_url).resolve()
            return str(resolved)
        except Exception:
            return None

    def get_link_graph(self) -> Dict[str, List[str]]:
        """Get the complete link graph"""
        return {path: list(links) for path, links in self.link_graph.items()}

    def find_broken_links(self, all_files: Set[str]) -> List[Tuple[str, str]]:
        """Find broken internal links"""
        broken_links = []

        for from_path, links in self.link_graph.items():
            for link in links:
                if link not in all_files:
                    broken_links.append((from_path, link))

        return broken_links


class DocScanner:
    """Main documentation scanning orchestrator"""

    def __init__(self):
        self.parser = MarkdownParser()
        self.link_analyzer = LinkGraphAnalyzer()

    async def scan_repository(self, request: DocScanRequest) -> DocScanResult:
        """Scan repository for documentation"""
        start_time = time.time()
        repo_path = Path(request.repo_path)

        if not repo_path.exists():
            return DocScanResult(
                project_id=request.project_id,
                repo_path=request.repo_path,
                docs=[],
                success=False,
                error_message=f"Repository path does not exist: {repo_path}",
                request_id=request.request_id
            )

        try:
            docs = []
            files_processed = 0

            # Default patterns if none specified
            doc_patterns = request.doc_patterns or [
                "**/*.md",
                "**/*.mdx",
                "**/*.markdown"
            ]

            # Find documentation files
            doc_files = []
            for pattern in doc_patterns:
                for file_path in repo_path.glob(pattern):
                    if file_path.is_file():
                        # Check include/exclude patterns
                        if self._should_include_file(file_path, request):
                            doc_files.append(file_path)

            # Process files
            semaphore = asyncio.Semaphore(20)  # Higher concurrency for docs

            async def process_doc_file(file_path: Path):
                async with semaphore:
                    nonlocal files_processed
                    doc = await self.parser.parse_file(file_path)
                    if doc:
                        doc.project_id = request.project_id
                        files_processed += 1
                        return doc
                    return None

            tasks = [process_doc_file(file_path) for file_path in doc_files]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.error("Error processing doc file", error=str(result))
                elif result:
                    docs.append(result)
                    if request.build_link_graph:
                        self.link_analyzer.add_document(result)

            duration = time.time() - start_time

            logger.info("Documentation scan completed",
                       project_id=request.project_id,
                       files_processed=files_processed,
                       docs_found=len(docs),
                       duration=duration)

            return DocScanResult(
                project_id=request.project_id,
                repo_path=request.repo_path,
                docs=docs,
                success=True,
                scan_duration=duration,
                files_processed=files_processed,
                request_id=request.request_id
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error("Documentation scan failed",
                        project_id=request.project_id,
                        error=str(e),
                        duration=duration)

            return DocScanResult(
                project_id=request.project_id,
                repo_path=request.repo_path,
                docs=[],
                success=False,
                error_message=str(e),
                scan_duration=duration,
                request_id=request.request_id
            )

    def _should_include_file(self, file_path: Path, request: DocScanRequest) -> bool:
        """Check if file should be included based on patterns"""
        # Check exclude patterns
        if request.exclude_patterns:
            for pattern in request.exclude_patterns:
                if file_path.match(pattern):
                    return False

        # Check include patterns
        if request.include_patterns:
            for pattern in request.include_patterns:
                if file_path.match(pattern):
                    return True
            return False

        return True


class ScanDocsWorker:
    """Main documentation scan worker"""

    def __init__(self, config: Dict):
        self.config = config
        self.redis_client = None
        self.nats_client = None
        self.scanner = DocScanner()

    async def initialize(self):
        """Initialize connections"""
        self.redis_client = redis.Redis(
            host=self.config.get("redis_host", "localhost"),
            port=self.config.get("redis_port", 6379),
            decode_responses=True
        )

        self.nats_client = NATS()
        await self.nats_client.connect(
            self.config.get("nats_url", "nats://localhost:4222")
        )

        logger.info("Documentation scan worker initialized")

    async def run(self):
        """Main worker loop"""
        await self.initialize()

        subject = "docs.scan"
        queue_group = "scan-docs-workers"

        logger.info("Subscribing to documentation scan requests",
                   subject=subject,
                   queue=queue_group)

        async def message_handler(msg):
            await self.handle_scan_request(msg)

        await self.nats_client.subscribe(
            subject,
            queue=queue_group,
            cb=message_handler
        )

        while True:
            await asyncio.sleep(1)

    async def handle_scan_request(self, msg):
        """Handle incoming scan request"""
        try:
            data = json.loads(msg.data.decode())
            request = DocScanRequest(**data)

            logger.info("Processing documentation scan request",
                       project_id=request.project_id,
                       repo_path=request.repo_path,
                       request_id=request.request_id)

            # Perform the scan
            result = await self.scanner.scan_repository(request)

            # Convert complex objects to serializable format
            result_data = {
                "project_id": result.project_id,
                "repo_path": result.repo_path,
                "docs": [asdict(doc) for doc in result.docs],
                "success": result.success,
                "error_message": result.error_message,
                "scan_duration": result.scan_duration,
                "files_processed": result.files_processed,
                "request_id": result.request_id,
                "timestamp": time.time()
            }

            result_subject = "docs.scan.result"
            await self.nats_client.publish(result_subject, json.dumps(result_data).encode())

            await msg.ack()

            logger.info("Documentation scan request processed",
                       project_id=request.project_id,
                       success=result.success,
                       docs_found=len(result.docs))

        except Exception as e:
            logger.error("Failed to process documentation scan request", error=str(e))

    async def shutdown(self):
        """Clean shutdown"""
        if self.nats_client:
            await self.nats_client.close()
        if self.redis_client:
            await self.redis_client.close()


async def main():
    """Main entry point"""
    config = {
        "redis_host": os.getenv("REDIS_HOST", "localhost"),
        "redis_port": int(os.getenv("REDIS_PORT", "6379")),
        "nats_url": os.getenv("NATS_URL", "nats://localhost:4222"),
    }

    worker = ScanDocsWorker(config)

    try:
        await worker.run()
    except Exception as e:
        logger.error("Worker failed", error=str(e))
        await worker.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
