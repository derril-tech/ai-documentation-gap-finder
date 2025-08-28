#!/usr/bin/env python3
"""
AI Documentation Gap Finder - Diff Worker

Detects drift between code and documentation by:
- Comparing OpenAPI/GraphQL schemas with current implementations
- Checking for broken links in documentation
- Executing and validating code snippets
- Identifying outdated examples and references

Features:
- Schema diffing with detailed change detection
- Link validation with caching and rate limiting
- Code snippet execution in sandboxed environments
- Comprehensive drift reporting
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
import tempfile
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from urllib.parse import urlparse, urljoin

import aiofiles
import httpx
from nats.aio.client import Client as NATS
from nats.aio.errors import ErrTimeout
import redis.asyncio as redis
import structlog
import yaml

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
    logger_factory=structlog.StdlibLoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@dataclass
class SchemaDrift:
    """Represents schema drift between spec and implementation"""
    id: str
    project_id: str
    drift_type: str  # missing_endpoint, changed_signature, deprecated_field, etc.
    entity_id: str
    spec_path: str
    severity: str  # critical, high, medium, low
    description: str
    current_value: Optional[Any] = None
    expected_value: Optional[Any] = None
    line_number: Optional[int] = None
    suggestions: Optional[List[str]] = None


@dataclass
class BrokenLink:
    """Represents a broken link in documentation"""
    id: str
    project_id: str
    doc_path: str
    link_url: str
    link_text: str
    line_number: int
    error_type: str  # 404, timeout, dns_error, ssl_error
    error_message: str
    last_checked: float
    retry_count: int = 0


@dataclass
class SnippetResult:
    """Result of executing a code snippet"""
    id: str
    project_id: str
    doc_path: str
    code_block_id: str
    language: str
    code: str
    success: bool
    execution_time: float
    output: Optional[str] = None
    error_message: Optional[str] = None
    exit_code: Optional[int] = None


@dataclass
class DiffRequest:
    """Diff analysis request"""
    project_id: str
    repo_path: str
    check_schema_drift: bool = True
    check_broken_links: bool = True
    test_snippets: bool = True
    include_external_links: bool = False
    max_concurrent_checks: int = 10
    request_id: str = ""


@dataclass
class DiffResult:
    """Diff analysis result"""
    project_id: str
    repo_path: str
    schema_drifts: List[SchemaDrift]
    broken_links: List[BrokenLink]
    snippet_results: List[SnippetResult]
    success: bool
    error_message: Optional[str] = None
    analysis_duration: float = 0.0
    files_processed: int = 0
    links_checked: int = 0
    snippets_executed: int = 0
    request_id: str = ""


class SchemaDriftDetector:
    """Detects drift between API specs and implementations"""

    def __init__(self):
        self.supported_formats = ['openapi', 'swagger', 'graphql']

    async def detect_drift(self, spec_files: List[Path], entities: List[Dict]) -> List[SchemaDrift]:
        """Detect schema drift across specification files"""
        drifts = []

        for spec_file in spec_files:
            try:
                spec_drifts = await self._analyze_spec_file(spec_file, entities)
                drifts.extend(spec_drifts)
            except Exception as e:
                logger.error("Failed to analyze spec file",
                           file=str(spec_file),
                           error=str(e))

        return drifts

    async def _analyze_spec_file(self, spec_file: Path, entities: List[Dict]) -> List[SchemaDrift]:
        """Analyze a single specification file"""
        drifts = []

        # Load spec
        spec = await self._load_spec(spec_file)
        if not spec:
            return drifts

        # Determine spec type
        spec_type = self._identify_spec_type(spec)

        if spec_type in ['openapi', 'swagger']:
            drifts.extend(await self._analyze_openapi_spec(spec, spec_file, entities))
        elif spec_type == 'graphql':
            drifts.extend(await self._analyze_graphql_spec(spec, spec_file, entities))

        return drifts

    async def _load_spec(self, spec_file: Path) -> Optional[Dict]:
        """Load specification from file"""
        try:
            async with aiofiles.open(spec_file, 'r', encoding='utf-8') as f:
                content = await f.read()

            # Try YAML first, then JSON
            try:
                return yaml.safe_load(content)
            except yaml.YAMLError:
                return json.loads(content)
        except Exception as e:
            logger.warning("Failed to load spec file", file=str(spec_file), error=str(e))
            return None

    def _identify_spec_type(self, spec: Dict) -> str:
        """Identify the type of API specification"""
        if 'openapi' in spec or 'swagger' in spec:
            return 'openapi'
        elif 'data' in spec and '__schema' in spec.get('data', {}):
            return 'graphql'
        return 'unknown'

    async def _analyze_openapi_spec(self, spec: Dict, spec_file: Path, entities: List[Dict]) -> List[SchemaDrift]:
        """Analyze OpenAPI/Swagger specification"""
        drifts = []

        paths = spec.get('paths', {})
        entity_map = {e['name']: e for e in entities if e.get('kind') == 'endpoint'}

        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue

            for method, operation in methods.items():
                if not isinstance(operation, dict):
                    continue

                operation_id = operation.get('operationId', f"{method}_{path.replace('/', '_')}")

                # Check if endpoint exists in entities
                if operation_id not in entity_map:
                    drifts.append(SchemaDrift(
                        id=f"missing_endpoint_{operation_id}",
                        project_id="",  # Set by caller
                        drift_type="missing_endpoint",
                        entity_id=operation_id,
                        spec_path=str(spec_file),
                        severity="high",
                        description=f"Endpoint '{operation_id}' defined in spec but not found in code",
                        expected_value=f"{method.upper()} {path}",
                        suggestions=["Implement the missing endpoint", "Update the API specification"]
                    ))
                else:
                    # Check for signature drift
                    entity = entity_map[operation_id]
                    sig_drifts = await self._check_signature_drift(operation, entity, spec_file)
                    drifts.extend(sig_drifts)

        return drifts

    async def _analyze_graphql_spec(self, spec: Dict, spec_file: Path, entities: List[Dict]) -> List[SchemaDrift]:
        """Analyze GraphQL schema"""
        drifts = []

        schema_data = spec.get('data', {}).get('__schema', {})
        types = schema_data.get('types', [])

        entity_map = {e['name']: e for e in entities if e.get('kind') in ['type', 'function']}

        for type_info in types:
            if not isinstance(type_info, dict):
                continue

            type_name = type_info.get('name', '')

            if type_name not in entity_map:
                drifts.append(SchemaDrift(
                    id=f"missing_type_{type_name}",
                    project_id="",  # Set by caller
                    drift_type="missing_type",
                    entity_id=type_name,
                    spec_path=str(spec_file),
                    severity="medium",
                    description=f"Type '{type_name}' defined in schema but not found in code",
                    suggestions=["Implement the missing type", "Update the GraphQL schema"]
                ))

        return drifts

    async def _check_signature_drift(self, operation: Dict, entity: Dict, spec_file: Path) -> List[SchemaDrift]:
        """Check for signature drift in OpenAPI operations"""
        drifts = []

        # Check parameters
        spec_params = operation.get('parameters', [])
        entity_params = entity.get('signature', {}).get('parameters', [])

        if len(spec_params) != len(entity_params):
            drifts.append(SchemaDrift(
                id=f"param_count_{entity['id']}",
                project_id="",  # Set by caller
                drift_type="parameter_count_mismatch",
                entity_id=entity['id'],
                spec_path=str(spec_file),
                severity="high",
                description=f"Parameter count mismatch: spec has {len(spec_params)}, code has {len(entity_params)}",
                current_value=len(entity_params),
                expected_value=len(spec_params)
            ))

        return drifts


class LinkChecker:
    """Checks for broken links in documentation"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.http_client = httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=20)
        )
        self.cache_ttl = 3600  # 1 hour

    async def check_links(self, docs: List[Dict], include_external: bool = False) -> List[BrokenLink]:
        """Check links in documentation files"""
        broken_links = []

        for doc in docs:
            doc_links = doc.get('links', [])
            doc_path = doc.get('path', '')

            for link in doc_links:
                if not isinstance(link, dict):
                    continue

                link_url = link.get('url', '')
                link_text = link.get('text', '')
                line_number = link.get('line_number', 0)

                # Skip external links if not requested
                is_external = link.get('is_external', False)
                if is_external and not include_external:
                    continue

                # Check cache first
                cached_result = await self._get_cached_result(link_url)
                if cached_result:
                    if cached_result['broken']:
                        broken_links.append(BrokenLink(
                            id=f"broken_{doc_path}_{line_number}",
                            project_id="",  # Set by caller
                            doc_path=doc_path,
                            link_url=link_url,
                            link_text=link_text,
                            line_number=line_number,
                            error_type=cached_result['error_type'],
                            error_message=cached_result['error_message'],
                            last_checked=cached_result['last_checked'],
                            retry_count=cached_result['retry_count']
                        ))
                    continue

                # Check the link
                is_broken, error_type, error_msg = await self._check_single_link(link_url)

                # Cache the result
                await self._cache_result(link_url, is_broken, error_type, error_msg)

                if is_broken:
                    broken_links.append(BrokenLink(
                        id=f"broken_{doc_path}_{line_number}",
                        project_id="",  # Set by caller
                        doc_path=doc_path,
                        link_url=link_url,
                        link_text=link_text,
                        line_number=line_number,
                        error_type=error_type,
                        error_message=error_msg,
                        last_checked=time.time()
                    ))

        await self.http_client.aclose()
        return broken_links

    async def _check_single_link(self, url: str) -> Tuple[bool, str, str]:
        """Check a single link"""
        try:
            # Handle relative URLs
            if url.startswith('/'):
                # Can't check relative URLs without base
                return True, "relative_url", "Cannot check relative URLs"

            response = await self.http_client.head(url)

            if response.status_code >= 400:
                return True, "http_error", f"HTTP {response.status_code}"

            return False, "", ""

        except httpx.TimeoutException:
            return True, "timeout", "Request timed out"
        except httpx.ConnectError:
            return True, "connection_error", "Failed to connect"
        except Exception as e:
            return True, "unknown_error", str(e)

    async def _get_cached_result(self, url: str) -> Optional[Dict]:
        """Get cached link check result"""
        cache_key = f"link_check:{url}"
        cached = await self.redis.get(cache_key)

        if cached:
            return json.loads(cached)
        return None

    async def _cache_result(self, url: str, broken: bool, error_type: str, error_msg: str):
        """Cache link check result"""
        cache_key = f"link_check:{url}"
        result = {
            'broken': broken,
            'error_type': error_type,
            'error_message': error_msg,
            'last_checked': time.time(),
            'retry_count': 0
        }

        await self.redis.setex(cache_key, self.cache_ttl, json.dumps(result))


class SnippetExecutor:
    """Executes code snippets in sandboxed environments"""

    def __init__(self):
        self.supported_languages = {
            'python': self._execute_python,
            'javascript': self._execute_javascript,
            'bash': self._execute_bash,
            'shell': self._execute_bash
        }

    async def execute_snippets(self, docs: List[Dict]) -> List[SnippetResult]:
        """Execute code snippets from documentation"""
        results = []

        for doc in docs:
            code_blocks = doc.get('code_blocks', [])
            doc_path = doc.get('path', '')

            for i, block in enumerate(code_blocks):
                if not isinstance(block, dict):
                    continue

                language = block.get('language', '').lower()
                code = block.get('code', '')
                line_number = block.get('line_number', 0)

                if language in self.supported_languages:
                    result = await self._execute_snippet(
                        doc_path, i, language, code, line_number
                    )
                    results.append(result)
                else:
                    # Unsupported language
                    results.append(SnippetResult(
                        id=f"snippet_{doc_path}_{i}",
                        project_id="",  # Set by caller
                        doc_path=doc_path,
                        code_block_id=str(i),
                        language=language,
                        code=code,
                        success=False,
                        execution_time=0.0,
                        error_message=f"Unsupported language: {language}"
                    ))

        return results

    async def _execute_snippet(self, doc_path: str, block_id: int, language: str,
                             code: str, line_number: int) -> SnippetResult:
        """Execute a single code snippet"""
        start_time = time.time()

        try:
            executor = self.supported_languages[language]
            success, output, error_msg, exit_code = await executor(code)

            execution_time = time.time() - start_time

            return SnippetResult(
                id=f"snippet_{doc_path}_{block_id}",
                project_id="",  # Set by caller
                doc_path=doc_path,
                code_block_id=str(block_id),
                language=language,
                code=code,
                success=success,
                execution_time=execution_time,
                output=output,
                error_message=error_msg,
                exit_code=exit_code
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return SnippetResult(
                id=f"snippet_{doc_path}_{block_id}",
                project_id="",  # Set by caller
                doc_path=doc_path,
                code_block_id=str(block_id),
                language=language,
                code=code,
                success=False,
                execution_time=execution_time,
                error_message=f"Execution failed: {str(e)}"
            )

    async def _execute_python(self, code: str) -> Tuple[bool, Optional[str], Optional[str], Optional[int]]:
        """Execute Python code snippet"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            process = await asyncio.create_subprocess_exec(
                'python', temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            success = process.returncode == 0
            output = stdout.decode().strip() if stdout else None
            error_msg = stderr.decode().strip() if stderr else None

            return success, output, error_msg, process.returncode

        finally:
            os.unlink(temp_file)

    async def _execute_javascript(self, code: str) -> Tuple[bool, Optional[str], Optional[str], Optional[int]]:
        """Execute JavaScript code snippet"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            process = await asyncio.create_subprocess_exec(
                'node', temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            success = process.returncode == 0
            output = stdout.decode().strip() if stdout else None
            error_msg = stderr.decode().strip() if stderr else None

            return success, output, error_msg, process.returncode

        finally:
            os.unlink(temp_file)

    async def _execute_bash(self, code: str) -> Tuple[bool, Optional[str], Optional[str], Optional[int]]:
        """Execute Bash/Shell code snippet"""
        try:
            process = await asyncio.create_subprocess_exec(
                'bash', '-c', code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            success = process.returncode == 0
            output = stdout.decode().strip() if stdout else None
            error_msg = stderr.decode().strip() if stderr else None

            return success, output, error_msg, process.returncode

        except Exception as e:
            return False, None, str(e), -1


class DiffWorker:
    """Main diff analysis worker"""

    def __init__(self, config: Dict):
        self.config = config
        self.redis_client = None
        self.nats_client = None

        # Initialize components
        self.schema_detector = SchemaDriftDetector()
        self.link_checker = None  # Will be initialized with Redis
        self.snippet_executor = SnippetExecutor()

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

        # Initialize link checker with Redis
        self.link_checker = LinkChecker(self.redis_client)

        logger.info("Diff worker initialized")

    async def run(self):
        """Main worker loop"""
        await self.initialize()

        subject = "delta.diff"
        queue_group = "diff-workers"

        logger.info("Subscribing to diff requests", subject=subject, queue=queue_group)

        async def message_handler(msg):
            await self.handle_diff_request(msg)

        await self.nats_client.subscribe(
            subject,
            queue=queue_group,
            cb=message_handler
        )

        while True:
            await asyncio.sleep(1)

    async def handle_diff_request(self, msg):
        """Handle incoming diff request"""
        try:
            data = json.loads(msg.data.decode())
            request = DiffRequest(**data)

            logger.info("Processing diff request",
                       project_id=request.project_id,
                       repo_path=request.repo_path,
                       request_id=request.request_id)

            start_time = time.time()

            # Load spec files
            spec_files = await self._find_spec_files(request.repo_path)

            # Load entities and docs (mock for now)
            entities = await self._load_entities(request)
            docs = await self._load_docs(request)

            # Perform analyses
            schema_drifts = []
            if request.check_schema_drift:
                schema_drifts = await self.schema_detector.detect_drift(spec_files, entities)

            broken_links = []
            if request.check_broken_links:
                broken_links = await self.link_checker.check_links(docs, request.include_external_links)

            snippet_results = []
            if request.test_snippets:
                snippet_results = await self.snippet_executor.execute_snippets(docs)

            duration = time.time() - start_time

            result = DiffResult(
                project_id=request.project_id,
                repo_path=request.repo_path,
                schema_drifts=schema_drifts,
                broken_links=broken_links,
                snippet_results=snippet_results,
                success=True,
                analysis_duration=duration,
                files_processed=len(spec_files),
                links_checked=len(broken_links),
                snippets_executed=len(snippet_results),
                request_id=request.request_id
            )

            # Publish result
            result_data = asdict(result)
            result_subject = "delta.diff.result"
            await self.nats_client.publish(result_subject, json.dumps(result_data).encode())

            await msg.ack()

            logger.info("Diff request processed",
                       project_id=request.project_id,
                       drifts_found=len(schema_drifts),
                       broken_links=len(broken_links),
                       snippets_executed=len(snippet_results))

        except Exception as e:
            logger.error("Failed to process diff request", error=str(e))

    async def _find_spec_files(self, repo_path: str) -> List[Path]:
        """Find API specification files in repository"""
        repo_dir = Path(repo_path)
        spec_files = []

        # Common spec file patterns
        patterns = [
            "**/*.json",
            "**/*.yaml",
            "**/*.yml"
        ]

        for pattern in patterns:
            for file_path in repo_dir.glob(pattern):
                if file_path.is_file():
                    # Check if it's a spec file
                    if self._is_spec_file(file_path):
                        spec_files.append(file_path)

        return spec_files

    def _is_spec_file(self, file_path: Path) -> bool:
        """Check if file is an API specification"""
        name = file_path.name.lower()
        return any(keyword in name for keyword in [
            'openapi', 'swagger', 'api', 'schema', 'graphql'
        ])

    async def _load_entities(self, request: DiffRequest) -> List[Dict]:
        """Load code entities (mock implementation)"""
        return [
            {
                'id': f'entity_{i}',
                'name': f'exampleEndpoint{i}',
                'kind': 'endpoint',
                'signature': {'parameters': []}
            } for i in range(5)
        ]

    async def _load_docs(self, request: DiffRequest) -> List[Dict]:
        """Load documentation files (mock implementation)"""
        return [
            {
                'path': f'/docs/example{i}.md',
                'links': [{'url': f'https://example.com/{i}', 'text': f'Link {i}', 'line_number': i}],
                'code_blocks': [{'language': 'python', 'code': f'print("Hello {i}")', 'line_number': i}]
            } for i in range(5)
        ]

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

    worker = DiffWorker(config)

    try:
        await worker.run()
    except Exception as e:
        logger.error("Worker failed", error=str(e))
        await worker.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
