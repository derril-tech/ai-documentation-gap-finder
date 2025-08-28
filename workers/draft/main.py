#!/usr/bin/env python3
"""
AI Documentation Gap Finder - Draft Worker

Auto-generates comprehensive documentation drafts in MDX format including:
- Document skeletons with proper frontmatter
- API reference tables with parameters, responses, examples
- Request/response examples in multiple languages
- Mermaid diagrams for flows and relationships
- Code snippets with syntax highlighting

Features:
- Template-based generation with customization
- Multi-language example generation
- Mermaid diagram generation from code analysis
- Frontmatter and metadata population
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
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
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
class DraftRequest:
    """Draft generation request"""
    project_id: str
    entity_id: Optional[str] = None
    doc_path: Optional[str] = None
    draft_type: str = "api_reference"  # api_reference, getting_started, troubleshooting, etc.
    include_examples: bool = True
    include_diagrams: bool = True
    languages: List[str] = None  # ["javascript", "python", "curl"]
    request_id: str = ""


@dataclass
class DraftResult:
    """Draft generation result"""
    project_id: str
    entity_id: Optional[str] = None
    doc_path: Optional[str] = None
    mdx_content: str
    frontmatter: Dict[str, Any]
    diagrams: List[Dict[str, Any]]
    examples: List[Dict[str, Any]]
    success: bool
    error_message: Optional[str] = None
    draft_duration: float = 0.0
    request_id: str = ""


@dataclass
class MDXSection:
    """Represents a section in MDX document"""
    title: str
    level: int = 2
    content: str = ""
    anchor: Optional[str] = None


class MDXGenerator:
    """Generates MDX documentation from code entities"""

    def __init__(self):
        self.templates = {
            "api_reference": self._generate_api_reference,
            "getting_started": self._generate_getting_started,
            "troubleshooting": self._generate_troubleshooting,
            "examples": self._generate_examples,
        }

    def generate_frontmatter(self, entity: Dict, project: Dict, draft_type: str) -> Dict[str, Any]:
        """Generate frontmatter for MDX document"""
        return {
            "title": entity.get("name", "API Reference"),
            "description": entity.get("docstring", "").split('.')[0] if entity.get("docstring") else "",
            "sidebar_position": 1,
            "draft_type": draft_type,
            "entity_id": entity.get("id"),
            "project_id": project.get("id"),
            "generated_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "tags": self._extract_tags(entity),
            "api_version": "v1",
            "languages": ["javascript", "python", "curl"],
        }

    def _extract_tags(self, entity: Dict) -> List[str]:
        """Extract relevant tags from entity"""
        tags = []

        if entity.get("kind") == "endpoint":
            tags.extend(["api", "endpoint", "rest"])
        elif entity.get("kind") == "function":
            tags.extend(["function", "code"])
        elif entity.get("kind") == "class":
            tags.extend(["class", "object"])

        if entity.get("visibility") == "public":
            tags.append("public")
        elif entity.get("visibility") == "internal":
            tags.append("internal")

        return tags

    async def generate_draft(self,
                           entity: Dict,
                           mappings: List[Dict],
                           project: Dict,
                           request: DraftRequest) -> DraftResult:
        """Generate complete MDX draft"""
        start_time = time.time()

        try:
            # Generate frontmatter
            frontmatter = self.generate_frontmatter(entity, project, request.draft_type)

            # Generate content based on type
            template_func = self.templates.get(request.draft_type, self._generate_api_reference)
            sections = await template_func(entity, mappings, project, request)

            # Generate diagrams if requested
            diagrams = []
            if request.include_diagrams:
                diagrams = await self._generate_diagrams(entity, mappings, request.draft_type)

            # Generate examples if requested
            examples = []
            if request.include_examples:
                examples = await self._generate_examples_section(entity, request.languages or ["javascript"])

            # Assemble MDX content
            mdx_content = self._assemble_mdx(frontmatter, sections, diagrams, examples)

            duration = time.time() - start_time

            return DraftResult(
                project_id=request.project_id,
                entity_id=request.entity_id,
                doc_path=request.doc_path,
                mdx_content=mdx_content,
                frontmatter=frontmatter,
                diagrams=diagrams,
                examples=examples,
                success=True,
                draft_duration=duration,
                request_id=request.request_id
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error("Draft generation failed",
                        entity_id=request.entity_id,
                        error=str(e),
                        duration=duration)

            return DraftResult(
                project_id=request.project_id,
                entity_id=request.entity_id,
                doc_path=request.doc_path,
                mdx_content="",
                frontmatter={},
                diagrams=[],
                examples=[],
                success=False,
                error_message=str(e),
                draft_duration=duration,
                request_id=request.request_id
            )

    async def _generate_api_reference(self,
                                    entity: Dict,
                                    mappings: List[Dict],
                                    project: Dict,
                                    request: DraftRequest) -> List[MDXSection]:
        """Generate API reference documentation"""
        sections = []

        # Overview section
        overview = f"""
# {entity.get('name', 'API Reference')}

{entity.get('docstring', 'API endpoint for ' + entity.get('name', 'unknown functionality'))}

## Overview

This API endpoint provides access to {entity.get('name', 'functionality')}.
"""

        sections.append(MDXSection(
            title="Overview",
            level=2,
            content=overview.strip(),
            anchor="overview"
        ))

        # Parameters section (if applicable)
        if entity.get("kind") == "endpoint" or entity.get("signature"):
            params_section = await self._generate_parameters_section(entity)
            if params_section:
                sections.append(params_section)

        # Request/Response section
        if entity.get("kind") == "endpoint":
            req_resp_section = await self._generate_request_response_section(entity)
            sections.append(req_resp_section)

        # Authentication section
        auth_section = MDXSection(
            title="Authentication",
            level=2,
            content="""
## Authentication

This endpoint requires authentication. Include your API key in the request headers:

```
Authorization: Bearer YOUR_API_KEY
```
""",
            anchor="authentication"
        )
        sections.append(auth_section)

        # Error handling section
        error_section = MDXSection(
            title="Error Handling",
            level=2,
            content="""
## Error Handling

The API uses standard HTTP status codes:

- `200` - Success
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error

Error responses include a JSON object with `error` and `message` fields.
""",
            anchor="error-handling"
        )
        sections.append(error_section)

        return sections

    async def _generate_getting_started(self,
                                      entity: Dict,
                                      mappings: List[Dict],
                                      project: Dict,
                                      request: DraftRequest) -> List[MDXSection]:
        """Generate getting started guide"""
        sections = []

        content = f"""
# Getting Started with {entity.get('name', 'API')}

Welcome to the {entity.get('name', 'API')} getting started guide.

## Prerequisites

Before you begin, ensure you have:

- API credentials
- Basic understanding of REST APIs
- A development environment

## Quick Start

Here's a simple example to get you started:

```bash
curl -X GET "{entity.get('name', 'api-endpoint')}" \\
  -H "Authorization: Bearer YOUR_API_KEY"
```

## Next Steps

1. [API Reference](./api-reference)
2. [Examples](./examples)
3. [Troubleshooting](./troubleshooting)
"""

        sections.append(MDXSection(
            title="Getting Started",
            level=1,
            content=content.strip(),
            anchor="getting-started"
        ))

        return sections

    async def _generate_troubleshooting(self,
                                      entity: Dict,
                                      mappings: List[Dict],
                                      project: Dict,
                                      request: DraftRequest) -> List[MDXSection]:
        """Generate troubleshooting guide"""
        sections = []

        content = f"""
# Troubleshooting {entity.get('name', 'API')}

Common issues and solutions for the {entity.get('name', 'API')}.

## Common Issues

### Authentication Errors

**Problem**: Receiving 401 Unauthorized errors.

**Solution**:
- Verify your API key is correct
- Check that the key is properly included in request headers
- Ensure the key hasn't expired

### Rate Limiting

**Problem**: Receiving 429 Too Many Requests errors.

**Solution**:
- Implement exponential backoff
- Check your current rate limit status
- Consider upgrading your plan for higher limits

### Data Format Issues

**Problem**: Receiving 400 Bad Request errors.

**Solution**:
- Validate your request payload format
- Check required vs optional parameters
- Review the API specification for correct data types
"""

        sections.append(MDXSection(
            title="Troubleshooting",
            level=1,
            content=content.strip(),
            anchor="troubleshooting"
        ))

        return sections

    async def _generate_examples(self,
                               entity: Dict,
                               mappings: List[Dict],
                               project: Dict,
                               request: DraftRequest) -> List[MDXSection]:
        """Generate examples section"""
        sections = []

        content = f"""
# {entity.get('name', 'API')} Examples

Practical examples for using the {entity.get('name', 'API')}.

## Basic Usage

```javascript
// JavaScript example
const response = await fetch('{entity.get('name', 'api-endpoint')}', {{
  method: 'GET',
  headers: {{
    'Authorization': 'Bearer YOUR_API_KEY',
    'Content-Type': 'application/json'
  }}
}});

const data = await response.json();
console.log(data);
```

```python
# Python example
import requests

response = requests.get(
    '{entity.get('name', 'api-endpoint')}',
    headers={{
        'Authorization': 'Bearer YOUR_API_KEY'
    }}
)

data = response.json()
print(data)
```

## Advanced Usage

For more complex scenarios, you can:

1. Handle pagination automatically
2. Implement retry logic
3. Use streaming responses
4. Batch multiple requests
"""

        sections.append(MDXSection(
            title="Examples",
            level=1,
            content=content.strip(),
            anchor="examples"
        ))

        return sections

    async def _generate_parameters_section(self, entity: Dict) -> Optional[MDXSection]:
        """Generate parameters table section"""
        signature = entity.get("signature", {})
        parameters = signature.get("parameters", [])

        if not parameters:
            return None

        # Create markdown table
        table_rows = [
            "| Parameter | Type | Required | Description |",
            "|-----------|------|----------|-------------|"
        ]

        for param in parameters:
            if isinstance(param, str):
                # Simple parameter name
                table_rows.append(f"| {param} | string | Yes | Parameter description |")
            elif isinstance(param, dict):
                name = param.get("name", "unknown")
                param_type = param.get("type", "string")
                required = "Yes" if param.get("required", False) else "No"
                desc = param.get("description", "Parameter description")
                table_rows.append(f"| {name} | {param_type} | {required} | {desc} |")

        content = f"""
## Parameters

{"\\n".join(table_rows)}
"""

        return MDXSection(
            title="Parameters",
            level=2,
            content=content.strip(),
            anchor="parameters"
        )

    async def _generate_request_response_section(self, entity: Dict) -> MDXSection:
        """Generate request/response examples section"""
        content = """
## Request

```http
GET /api/endpoint HTTP/1.1
Host: api.example.com
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

## Response

### Success Response (200 OK)

```json
{
  "success": true,
  "data": {
    "id": "123",
    "name": "Example Item",
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### Error Response (400 Bad Request)

```json
{
  "success": false,
  "error": "VALIDATION_ERROR",
  "message": "Invalid request parameters"
}
```
"""

        return MDXSection(
            title="Request & Response",
            level=2,
            content=content.strip(),
            anchor="request-response"
        )

    async def _generate_diagrams(self,
                               entity: Dict,
                               mappings: List[Dict],
                               draft_type: str) -> List[Dict[str, Any]]:
        """Generate Mermaid diagrams"""
        diagrams = []

        if draft_type == "api_reference":
            # API flow diagram
            diagram = {
                "type": "flowchart",
                "title": "API Flow",
                "content": """
```mermaid
flowchart TD
    A[Client Request] --> B[Authentication]
    B --> C{Valid Token?}
    C -->|Yes| D[Process Request]
    C -->|No| E[Return 401]
    D --> F[Business Logic]
    F --> G[Database Query]
    G --> H[Format Response]
    H --> I[Return 200]
```
"""
            }
            diagrams.append(diagram)

        elif draft_type == "getting_started":
            # Getting started flow
            diagram = {
                "type": "flowchart",
                "title": "Getting Started Flow",
                "content": """
```mermaid
flowchart LR
    A[Sign Up] --> B[Get API Key]
    B --> C[Make First Request]
    C --> D[Handle Response]
    D --> E[Build Integration]
    E --> F[Go Live]
```
"""
            }
            diagrams.append(diagram)

        return diagrams

    async def _generate_examples_section(self,
                                       entity: Dict,
                                       languages: List[str]) -> List[Dict[str, Any]]:
        """Generate code examples in multiple languages"""
        examples = []

        for language in languages:
            if language == "javascript":
                example = {
                    "language": "javascript",
                    "title": "JavaScript Example",
                    "code": f"""
// JavaScript example for {entity.get('name', 'API')}
const apiCall = async () => {{
  try {{
    const response = await fetch('{entity.get('name', 'api-endpoint')}', {{
      method: 'GET',
      headers: {{
        'Authorization': 'Bearer YOUR_API_KEY',
        'Content-Type': 'application/json'
      }}
    }});

    if (!response.ok) {{
      throw new Error(`HTTP error! status: ${{response.status}}`);
    }}

    const data = await response.json();
    console.log('API Response:', data);
    return data;
  }} catch (error) {{
    console.error('API call failed:', error);
    throw error;
  }}
}};

// Usage
apiCall().then(data => console.log(data));
"""
                }
                examples.append(example)

            elif language == "python":
                example = {
                    "language": "python",
                    "title": "Python Example",
                    "code": f"""
# Python example for {entity.get('name', 'API')}
import requests
from typing import Dict, Any

def call_api() -> Dict[str, Any]:
    \"\"\"
    Call the {entity.get('name', 'API')} endpoint
    \"\"\"
    url = "{entity.get('name', 'api-endpoint')}"
    headers = {{
        "Authorization": "Bearer YOUR_API_KEY",
        "Content-Type": "application/json"
    }}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise exception for bad status codes

        data = response.json()
        print(f"API Response: {{data}}")
        return data

    except requests.exceptions.RequestException as e:
        print(f"API call failed: {{e}}")
        raise

# Usage
if __name__ == "__main__":
    result = call_api()
    print("Success:", result)
"""
                }
                examples.append(example)

            elif language == "curl":
                example = {
                    "language": "bash",
                    "title": "cURL Example",
                    "code": f"""
# cURL example for {entity.get('name', 'API')}
curl -X GET "{entity.get('name', 'api-endpoint')}" \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -v
"""
                }
                examples.append(example)

        return examples

    def _assemble_mdx(self,
                    frontmatter: Dict[str, Any],
                    sections: List[MDXSection],
                    diagrams: List[Dict[str, Any]],
                    examples: List[Dict[str, Any]]) -> str:
        """Assemble complete MDX document"""
        lines = []

        # Frontmatter
        if frontmatter:
            lines.append("---")
            for key, value in frontmatter.items():
                if isinstance(value, list):
                    lines.append(f"{key}:")
                    for item in value:
                        lines.append(f"  - {item}")
                else:
                    lines.append(f"{key}: {value}")
            lines.append("---")
            lines.append("")

        # Sections
        for section in sections:
            # Add heading
            lines.append("#" * section.level + " " + section.title)
            lines.append("")

            # Add content
            if section.content:
                lines.append(section.content)
                lines.append("")

        # Diagrams
        if diagrams:
            lines.append("## Diagrams")
            lines.append("")
            for diagram in diagrams:
                lines.append(f"### {diagram['title']}")
                lines.append("")
                lines.append(diagram['content'])
                lines.append("")

        # Examples
        if examples:
            lines.append("## Code Examples")
            lines.append("")
            for example in examples:
                lines.append(f"### {example['title']}")
                lines.append("")
                lines.append(f"```{example['language']}")
                lines.append(example['code'].strip())
                lines.append("```")
                lines.append("")

        return "\n".join(lines)


class DraftWorker:
    """Main draft generation worker"""

    def __init__(self, config: Dict):
        self.config = config
        self.redis_client = None
        self.nats_client = None
        self.mdx_generator = MDXGenerator()

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

        logger.info("Draft worker initialized")

    async def run(self):
        """Main worker loop"""
        await self.initialize()

        subject = "docs.draft"
        queue_group = "draft-workers"

        logger.info("Subscribing to draft requests", subject=subject, queue=queue_group)

        async def message_handler(msg):
            await self.handle_draft_request(msg)

        await self.nats_client.subscribe(
            subject,
            queue=queue_group,
            cb=message_handler
        )

        while True:
            await asyncio.sleep(1)

    async def handle_draft_request(self, msg):
        """Handle incoming draft request"""
        try:
            data = json.loads(msg.data.decode())
            request = DraftRequest(**data)

            logger.info("Processing draft request",
                       project_id=request.project_id,
                       entity_id=request.entity_id,
                       draft_type=request.draft_type,
                       request_id=request.request_id)

            # Get entity and project data (mock for now)
            entity = await self._get_entity_data(request.entity_id)
            mappings = await self._get_mappings_data(request.project_id, request.entity_id)
            project = await self._get_project_data(request.project_id)

            # Generate draft
            result = await self.mdx_generator.generate_draft(entity, mappings, project, request)

            # Publish result
            result_data = asdict(result)
            result_subject = "docs.draft.result"
            await self.nats_client.publish(result_subject, json.dumps(result_data).encode())

            await msg.ack()

            logger.info("Draft request processed",
                       project_id=request.project_id,
                       success=result.success,
                       content_length=len(result.mdx_content))

        except Exception as e:
            logger.error("Failed to process draft request", error=str(e))

    async def _get_entity_data(self, entity_id: Optional[str]) -> Dict[str, Any]:
        """Get entity data (mock implementation)"""
        return {
            "id": entity_id or "mock_entity",
            "name": "UserAPI",
            "kind": "endpoint",
            "path": "/src/api/user.py",
            "lang": "python",
            "signature": {
                "parameters": [
                    {"name": "user_id", "type": "string", "required": True, "description": "User ID"},
                    {"name": "include", "type": "string", "required": False, "description": "Additional data to include"}
                ]
            },
            "docstring": "API endpoint for retrieving user information",
            "visibility": "public"
        }

    async def _get_mappings_data(self, project_id: str, entity_id: Optional[str]) -> List[Dict[str, Any]]:
        """Get mappings data (mock implementation)"""
        return [
            {
                "entity_id": entity_id,
                "doc_id": "doc_1",
                "score": 0.85,
                "relation": "describes"
            }
        ]

    async def _get_project_data(self, project_id: str) -> Dict[str, Any]:
        """Get project data (mock implementation)"""
        return {
            "id": project_id,
            "name": "Sample Project",
            "code_repo": "https://github.com/example/repo",
            "docs_repo": "https://github.com/example/docs"
        }

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

    worker = DraftWorker(config)

    try:
        await worker.run()
    except Exception as e:
        logger.error("Worker failed", error=str(e))
        await worker.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
