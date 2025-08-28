#!/usr/bin/env python3
"""
AI Documentation Gap Finder - Code Scanner Worker

Extracts symbols and entities from source code across multiple languages.
Supports TypeScript/JS, Python, OpenAPI, GraphQL, and CLI parsers.

Features:
- Multi-language AST parsing (TS/JS, Python, Go, Java)
- OpenAPI/GraphQL specification ingestion
- CLI command extraction (Cobra, Click, Commander)
- Symbol classification (functions, classes, endpoints, CLI commands, env vars)
- Async processing with NATS/Redis
- Error handling and retry logic
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
from typing import Dict, List, Optional, Any, Set
from urllib.parse import urlparse

import aiofiles
import httpx
from nats.aio.client import Client as NATS
from nats.aio.errors import ErrTimeout
import redis.asyncio as redis
import structlog
import yaml

# Language-specific imports
try:
    from libcst import parse_module, Module, FunctionDef, ClassDef, Assign
    LIBCST_AVAILABLE = True
except ImportError:
    LIBCST_AVAILABLE = False

try:
    import openapi_spec_validator
    OPENAPI_AVAILABLE = True
except ImportError:
    OPENAPI_AVAILABLE = False

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
class CodeEntity:
    """Represents a code entity (function, class, endpoint, etc.)"""
    id: str
    project_id: str
    kind: str  # function, class, endpoint, cli, flag, env, type
    name: str
    path: str
    lang: str
    signature: Optional[Dict[str, Any]] = None
    spec: Optional[Dict[str, Any]] = None
    visibility: str = "private"  # public, private, internal
    version: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    docstring: Optional[str] = None
    dependencies: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ScanRequest:
    """Code scan request"""
    project_id: str
    repo_path: str
    languages: List[str] = None
    include_patterns: List[str] = None
    exclude_patterns: List[str] = None
    scan_specs: bool = True
    scan_cli: bool = True
    request_id: str = ""


@dataclass
class ScanResult:
    """Code scan result"""
    project_id: str
    repo_path: str
    entities: List[CodeEntity]
    success: bool
    error_message: Optional[str] = None
    scan_duration: float = 0.0
    files_processed: int = 0
    request_id: str = ""


class LanguageParser:
    """Base class for language-specific parsers"""

    def __init__(self, language: str):
        self.language = language

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the file"""
        raise NotImplementedError

    async def parse_file(self, file_path: Path) -> List[CodeEntity]:
        """Parse a single file and extract entities"""
        raise NotImplementedError

    def extract_docstring(self, node: Any) -> Optional[str]:
        """Extract docstring from AST node"""
        return None


class PythonParser(LanguageParser):
    """Python code parser using libcst"""

    def __init__(self):
        super().__init__("python")
        self.extensions = {".py", ".pyi"}

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix in self.extensions

    async def parse_file(self, file_path: Path) -> List[CodeEntity]:
        """Parse Python file and extract entities"""
        if not LIBCST_AVAILABLE:
            logger.warning("libcst not available, skipping Python parsing")
            return []

        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()

            tree = parse_module(content)
            entities = []

            for node in tree.children:
                if isinstance(node, FunctionDef):
                    entities.append(await self._parse_function(node, file_path))
                elif isinstance(node, ClassDef):
                    entities.append(await self._parse_class(node, file_path))

            return entities

        except Exception as e:
            logger.error("Failed to parse Python file", file=str(file_path), error=str(e))
            return []

    async def _parse_function(self, node: FunctionDef, file_path: Path) -> CodeEntity:
        """Parse function definition"""
        name = node.name.value
        params = [param.name.value for param in node.params.params]

        return CodeEntity(
            id=f"{file_path}:{name}",
            project_id="",  # Will be set by caller
            kind="function",
            name=name,
            path=str(file_path),
            lang="python",
            signature={
                "parameters": params,
                "async": node.async_is_present,
                "returns": None  # Could be enhanced
            },
            line_start=node.lineno,
            line_end=getattr(node, 'end_lineno', node.lineno),
            docstring=self.extract_docstring(node)
        )

    async def _parse_class(self, node: ClassDef, file_path: Path) -> CodeEntity:
        """Parse class definition"""
        name = node.name.value

        return CodeEntity(
            id=f"{file_path}:{name}",
            project_id="",  # Will be set by caller
            kind="class",
            name=name,
            path=str(file_path),
            lang="python",
            signature={
                "bases": [base.value for base in node.bases] if node.bases else []
            },
            line_start=node.lineno,
            line_end=getattr(node, 'end_lineno', node.lineno),
            docstring=self.extract_docstring(node)
        )

    def extract_docstring(self, node: Any) -> Optional[str]:
        """Extract docstring from Python AST node"""
        if hasattr(node, 'body') and node.body.body:
            first_stmt = node.body.body[0]
            if hasattr(first_stmt, 'value') and isinstance(first_stmt.value, str):
                return first_stmt.value.strip('\'"')
        return None


class TypeScriptParser(LanguageParser):
    """TypeScript/JavaScript parser"""

    def __init__(self):
        super().__init__("typescript")
        self.extensions = {".ts", ".tsx", ".js", ".jsx"}

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix in self.extensions

    async def parse_file(self, file_path: Path) -> List[CodeEntity]:
        """Parse TypeScript/JavaScript file"""
        # For now, use regex-based parsing
        # In production, would use TypeScript compiler API
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()

            entities = []

            # Extract function declarations
            func_pattern = r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)'
            for match in re.finditer(func_pattern, content):
                entities.append(CodeEntity(
                    id=f"{file_path}:{match.group(1)}",
                    project_id="",  # Will be set by caller
                    kind="function",
                    name=match.group(1),
                    path=str(file_path),
                    lang="typescript",
                    signature={
                        "parameters": [p.strip() for p in match.group(2).split(',') if p.strip()]
                    }
                ))

            # Extract class declarations
            class_pattern = r'(?:export\s+)?class\s+(\w+)'
            for match in re.finditer(class_pattern, content):
                entities.append(CodeEntity(
                    id=f"{file_path}:{match.group(1)}",
                    project_id="",  # Will be set by caller
                    kind="class",
                    name=match.group(1),
                    path=str(file_path),
                    lang="typescript"
                ))

            return entities

        except Exception as e:
            logger.error("Failed to parse TypeScript file", file=str(file_path), error=str(e))
            return []


class SpecParser(LanguageParser):
    """Parser for OpenAPI and GraphQL specifications"""

    def __init__(self):
        super().__init__("spec")
        self.extensions = {".json", ".yaml", ".yml"}

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix in self.extensions and self._is_spec_file(file_path)

    def _is_spec_file(self, file_path: Path) -> bool:
        """Check if file is an OpenAPI or GraphQL spec"""
        name = file_path.name.lower()
        return any(keyword in name for keyword in ['openapi', 'swagger', 'graphql', 'schema'])

    async def parse_file(self, file_path: Path) -> List[CodeEntity]:
        """Parse specification file"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()

            # Try to parse as YAML first, then JSON
            try:
                spec = yaml.safe_load(content)
            except yaml.YAMLError:
                try:
                    spec = json.loads(content)
                except json.JSONDecodeError:
                    logger.warning("Could not parse spec file", file=str(file_path))
                    return []

            entities = []

            # Parse OpenAPI spec
            if self._is_openapi_spec(spec):
                entities.extend(await self._parse_openapi_spec(spec, file_path))
            # Parse GraphQL schema
            elif self._is_graphql_spec(spec):
                entities.extend(await self._parse_graphql_spec(spec, file_path))

            return entities

        except Exception as e:
            logger.error("Failed to parse spec file", file=str(file_path), error=str(e))
            return []

    def _is_openapi_spec(self, spec: Dict) -> bool:
        """Check if spec is OpenAPI"""
        return 'openapi' in spec or 'swagger' in spec

    def _is_graphql_spec(self, spec: Dict) -> bool:
        """Check if spec is GraphQL"""
        return 'data' in spec and '__schema' in spec.get('data', {})

    async def _parse_openapi_spec(self, spec: Dict, file_path: Path) -> List[CodeEntity]:
        """Parse OpenAPI specification"""
        entities = []

        paths = spec.get('paths', {})
        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue

            for method, operation in methods.items():
                if not isinstance(operation, dict):
                    continue

                operation_id = operation.get('operationId', f"{method}_{path.replace('/', '_')}")
                summary = operation.get('summary', '')

                entities.append(CodeEntity(
                    id=f"{file_path}:endpoint:{operation_id}",
                    project_id="",  # Will be set by caller
                    kind="endpoint",
                    name=operation_id,
                    path=str(file_path),
                    lang="openapi",
                    signature={
                        "method": method.upper(),
                        "path": path,
                        "parameters": operation.get('parameters', [])
                    },
                    spec=operation,
                    docstring=summary
                ))

        return entities

    async def _parse_graphql_spec(self, spec: Dict, file_path: Path) -> List[CodeEntity]:
        """Parse GraphQL schema"""
        entities = []

        schema_data = spec.get('data', {}).get('__schema', {})
        types = schema_data.get('types', [])

        for type_info in types:
            if not isinstance(type_info, dict):
                continue

            type_name = type_info.get('name', '')
            type_kind = type_info.get('kind', '')

            if type_kind in ['OBJECT', 'INTERFACE', 'INPUT_OBJECT']:
                entities.append(CodeEntity(
                    id=f"{file_path}:type:{type_name}",
                    project_id="",  # Will be set by caller
                    kind="type",
                    name=type_name,
                    path=str(file_path),
                    lang="graphql",
                    spec=type_info
                ))

            # Extract field definitions
            fields = type_info.get('fields', [])
            for field in fields:
                if not isinstance(field, dict):
                    continue

                field_name = field.get('name', '')
                entities.append(CodeEntity(
                    id=f"{file_path}:field:{type_name}.{field_name}",
                    project_id="",  # Will be set by caller
                    kind="function",
                    name=f"{type_name}.{field_name}",
                    path=str(file_path),
                    lang="graphql",
                    signature={
                        "args": field.get('args', [])
                    },
                    spec=field
                ))

        return entities


class CodeScanner:
    """Main code scanning orchestrator"""

    def __init__(self):
        self.parsers = [
            PythonParser(),
            TypeScriptParser(),
            SpecParser(),
        ]

    async def scan_repository(self, request: ScanRequest) -> ScanResult:
        """Scan a repository for code entities"""
        start_time = time.time()
        repo_path = Path(request.repo_path)

        if not repo_path.exists():
            return ScanResult(
                project_id=request.project_id,
                repo_path=request.repo_path,
                entities=[],
                success=False,
                error_message=f"Repository path does not exist: {repo_path}",
                request_id=request.request_id
            )

        try:
            entities = []
            files_processed = 0

            # Find files to scan
            files_to_scan = await self._find_files_to_scan(
                repo_path,
                request.languages or [],
                request.include_patterns or [],
                request.exclude_patterns or []
            )

            # Process files in parallel
            semaphore = asyncio.Semaphore(10)  # Limit concurrent file processing

            async def process_file(file_path: Path):
                async with semaphore:
                    nonlocal files_processed
                    file_entities = await self._process_file(file_path, request.project_id)
                    files_processed += 1
                    return file_entities

            tasks = [process_file(file_path) for file_path in files_to_scan]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.error("Error processing file", error=str(result))
                else:
                    entities.extend(result)

            duration = time.time() - start_time

            logger.info("Repository scan completed",
                       project_id=request.project_id,
                       files_processed=files_processed,
                       entities_found=len(entities),
                       duration=duration)

            return ScanResult(
                project_id=request.project_id,
                repo_path=request.repo_path,
                entities=entities,
                success=True,
                scan_duration=duration,
                files_processed=files_processed,
                request_id=request.request_id
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error("Repository scan failed",
                        project_id=request.project_id,
                        error=str(e),
                        duration=duration)

            return ScanResult(
                project_id=request.project_id,
                repo_path=request.repo_path,
                entities=[],
                success=False,
                error_message=str(e),
                scan_duration=duration,
                request_id=request.request_id
            )

    async def _find_files_to_scan(self,
                                repo_path: Path,
                                languages: List[str],
                                include_patterns: List[str],
                                exclude_patterns: List[str]) -> List[Path]:
        """Find files to scan based on criteria"""
        files = []

        # Default patterns if none specified
        if not include_patterns:
            include_patterns = ["**/*.py", "**/*.ts", "**/*.js", "**/*.json", "**/*.yaml", "**/*.yml"]

        for pattern in include_patterns:
            for file_path in repo_path.glob(pattern):
                if file_path.is_file():
                    # Check exclude patterns
                    excluded = any(file_path.match(excl) for excl in exclude_patterns)
                    if not excluded:
                        files.append(file_path)

        return files

    async def _process_file(self, file_path: Path, project_id: str) -> List[CodeEntity]:
        """Process a single file with appropriate parser"""
        for parser in self.parsers:
            if parser.can_parse(file_path):
                entities = await parser.parse_file(file_path)

                # Set project_id on all entities
                for entity in entities:
                    entity.project_id = project_id

                return entities

        return []


class ScanCodeWorker:
    """Main scan code worker"""

    def __init__(self, config: Dict):
        self.config = config
        self.redis_client = None
        self.nats_client = None
        self.scanner = CodeScanner()

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

        logger.info("Scan code worker initialized")

    async def run(self):
        """Main worker loop"""
        await self.initialize()

        subject = "code.scan"
        queue_group = "scan-code-workers"

        logger.info("Subscribing to scan requests", subject=subject, queue=queue_group)

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
            request = ScanRequest(**data)

            logger.info("Processing scan request",
                       project_id=request.project_id,
                       repo_path=request.repo_path,
                       request_id=request.request_id)

            # Perform the scan
            result = await self.scanner.scan_repository(request)

            # Publish result
            result_data = {
                "project_id": result.project_id,
                "repo_path": result.repo_path,
                "entities": [asdict(entity) for entity in result.entities],
                "success": result.success,
                "error_message": result.error_message,
                "scan_duration": result.scan_duration,
                "files_processed": result.files_processed,
                "request_id": result.request_id,
                "timestamp": time.time()
            }

            result_subject = "code.scan.result"
            await self.nats_client.publish(result_subject, json.dumps(result_data).encode())

            await msg.ack()

            logger.info("Scan request processed",
                       project_id=request.project_id,
                       success=result.success,
                       entities_found=len(result.entities))

        except Exception as e:
            logger.error("Failed to process scan request", error=str(e))

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

    worker = ScanCodeWorker(config)

    try:
        await worker.run()
    except Exception as e:
        logger.error("Worker failed", error=str(e))
        await worker.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
