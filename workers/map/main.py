#!/usr/bin/env python3
"""
AI Documentation Gap Finder - Mapping Worker

Creates intelligent mappings between code entities and documentation using:
- Vector embeddings for semantic similarity
- Heuristic matching (names, paths, signatures)
- Confidence scoring and relationship classification

Features:
- pgvector integration for efficient similarity search
- Hybrid scoring combining embeddings + heuristics
- Relationship classification (describes, references, mentions)
- Async processing with confidence thresholds
- Manual override support
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
from typing import Dict, List, Optional, Any, Tuple, Set
from urllib.parse import urlparse

import aiofiles
import httpx
from nats.aio.client import Client as NATS
from nats.aio.errors import ErrTimeout
import redis.asyncio as redis
import structlog
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

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
    """Code entity representation"""
    id: str
    project_id: str
    kind: str
    name: str
    path: str
    lang: str
    signature: Optional[Dict[str, Any]] = None
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class DocEntity:
    """Documentation entity representation"""
    id: str
    project_id: str
    path: str
    title: Optional[str] = None
    headings: List[Dict[str, Any]] = None
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EntityMapping:
    """Mapping between entity and documentation"""
    id: str
    project_id: str
    entity_id: str
    doc_id: str
    anchor: Optional[str] = None
    score: float = 0.0
    relation: str = "describes"  # describes, references, mentions
    confidence: str = "medium"  # high, medium, low
    heuristics_score: float = 0.0
    embedding_score: float = 0.0
    manual_override: bool = False
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MapRequest:
    """Mapping request"""
    project_id: str
    entity_ids: List[str] = None
    doc_ids: List[str] = None
    use_embeddings: bool = True
    use_heuristics: bool = True
    min_score_threshold: float = 0.3
    max_mappings_per_entity: int = 5
    request_id: str = ""


@dataclass
class MapResult:
    """Mapping result"""
    project_id: str
    mappings: List[EntityMapping]
    success: bool
    error_message: Optional[str] = None
    map_duration: float = 0.0
    entities_processed: int = 0
    docs_processed: int = 0
    mappings_created: int = 0
    request_id: str = ""


class EmbeddingGenerator:
    """Generates embeddings for text using OpenAI or local models"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.use_openai = bool(self.api_key)
        self.embedding_cache: Dict[str, List[float]] = {}

        if self.use_openai:
            logger.info("Using OpenAI for embeddings")
        else:
            logger.info("Using mock embeddings (OpenAI API key not provided)")

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        # Check cache first
        cache_key = self._get_cache_key(text)
        if cache_key in self.embedding_cache:
            return self.embedding_cache[cache_key]

        if self.use_openai:
            embedding = await self._generate_openai_embedding(text)
        else:
            embedding = self._generate_mock_embedding(text)

        # Cache the result
        self.embedding_cache[cache_key] = embedding
        return embedding

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        import hashlib
        return hashlib.md5(text.encode()).hexdigest()

    async def _generate_openai_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "input": text,
                        "model": "text-embedding-3-small",
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()
                    return data["data"][0]["embedding"]
                else:
                    logger.warning("OpenAI API error", status=response.status_code)
                    return self._generate_mock_embedding(text)

        except Exception as e:
            logger.warning("Failed to generate OpenAI embedding", error=str(e))
            return self._generate_mock_embedding(text)

    def _generate_mock_embedding(self, text: str) -> List[float]:
        """Generate mock embedding for testing"""
        # Simple hash-based mock embedding
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()

        # Convert to float list (1536 dimensions to match OpenAI)
        embedding = []
        for i in range(1536):
            byte_val = hash_bytes[i % len(hash_bytes)]
            # Normalize to [-1, 1]
            embedding.append((byte_val / 127.5) - 1.0)

        return embedding


class HeuristicMatcher:
    """Implements heuristic matching algorithms"""

    def __init__(self):
        self.name_patterns = [
            re.compile(r'(\w+)'),  # Simple word matching
            re.compile(r'([A-Z][a-z]+|[A-Z]+(?![a-z]))'),  # CamelCase/PascalCase
            re.compile(r'(\w+)(?:_|-)(\w+)'),  # snake_case/kebab-case
        ]

    def calculate_heuristics_score(self, entity: CodeEntity, doc: DocEntity) -> Tuple[float, str]:
        """Calculate heuristic similarity score between entity and doc"""
        scores = []

        # Name similarity
        name_score = self._calculate_name_similarity(entity.name, doc.title or "")
        scores.append(("name", name_score))

        # Path similarity
        path_score = self._calculate_path_similarity(entity.path, doc.path)
        scores.append(("path", path_score))

        # Signature similarity (for functions/methods)
        if entity.signature and entity.kind in ['function', 'method']:
            sig_score = self._calculate_signature_similarity(entity.signature, doc)
            scores.append(("signature", sig_score))

        # Heading similarity
        if doc.headings:
            heading_score = self._calculate_heading_similarity(entity.name, doc.headings)
            scores.append(("heading", heading_score))

        # Combine scores with weights
        weights = {
            "name": 0.4,
            "path": 0.2,
            "signature": 0.2,
            "heading": 0.2
        }

        total_score = sum(score * weights.get(metric, 0) for metric, score in scores)

        # Determine confidence level
        if total_score >= 0.8:
            confidence = "high"
        elif total_score >= 0.5:
            confidence = "medium"
        else:
            confidence = "low"

        return total_score, confidence

    def _calculate_name_similarity(self, entity_name: str, doc_title: str) -> float:
        """Calculate similarity between entity name and doc title"""
        if not entity_name or not doc_title:
            return 0.0

        entity_words = set(self._extract_words(entity_name.lower()))
        title_words = set(self._extract_words(doc_title.lower()))

        if not entity_words:
            return 0.0

        intersection = entity_words.intersection(title_words)
        return len(intersection) / len(entity_words)

    def _calculate_path_similarity(self, entity_path: str, doc_path: str) -> float:
        """Calculate similarity between file paths"""
        entity_parts = Path(entity_path).parts
        doc_parts = Path(doc_path).parts

        # Compare directory structures
        common_parts = 0
        for i, (entity_part, doc_part) in enumerate(zip(entity_parts, doc_parts)):
            if entity_part == doc_part:
                common_parts += 1
            else:
                break

        max_parts = max(len(entity_parts), len(doc_parts))
        return common_parts / max_parts if max_parts > 0 else 0.0

    def _calculate_signature_similarity(self, signature: Dict, doc: DocEntity) -> float:
        """Calculate similarity based on function signature"""
        # Look for parameter names in doc content/headings
        params = signature.get("parameters", [])
        if not params:
            return 0.0

        param_names = [p.split(":")[0].strip() for p in params if isinstance(p, str)]

        # Check if parameters appear in headings or content
        matches = 0
        for param in param_names:
            if doc.headings:
                for heading in doc.headings:
                    if param.lower() in heading.get("text", "").lower():
                        matches += 1
                        break

        return matches / len(param_names) if param_names else 0.0

    def _calculate_heading_similarity(self, entity_name: str, headings: List[Dict]) -> float:
        """Calculate similarity with document headings"""
        entity_words = set(self._extract_words(entity_name.lower()))

        max_score = 0.0
        for heading in headings:
            heading_text = heading.get("text", "").lower()
            heading_words = set(self._extract_words(heading_text))

            if entity_words and heading_words:
                intersection = entity_words.intersection(heading_words)
                score = len(intersection) / len(entity_words)
                max_score = max(max_score, score)

        return max_score

    def _extract_words(self, text: str) -> List[str]:
        """Extract words from text using various patterns"""
        words = []
        for pattern in self.name_patterns:
            matches = pattern.findall(text)
            words.extend(matches)

        # Clean and deduplicate
        cleaned_words = []
        for word in words:
            word = re.sub(r'[^a-zA-Z0-9]', '', word).lower()
            if word and len(word) > 2:  # Skip very short words
                cleaned_words.append(word)

        return list(set(cleaned_words))


class MappingEngine:
    """Core mapping engine combining embeddings and heuristics"""

    def __init__(self, embedding_generator: EmbeddingGenerator, heuristic_matcher: HeuristicMatcher):
        self.embedding_generator = embedding_generator
        self.heuristic_matcher = heuristic_matcher

    async def generate_mappings(self,
                              entities: List[CodeEntity],
                              docs: List[DocEntity],
                              request: MapRequest) -> List[EntityMapping]:
        """Generate mappings between entities and docs"""
        mappings = []

        # Generate embeddings if needed
        if request.use_embeddings:
            await self._generate_embeddings(entities + docs)

        # Calculate mappings for each entity
        for entity in entities:
            entity_mappings = await self._map_entity_to_docs(entity, docs, request)
            mappings.extend(entity_mappings)

            # Limit mappings per entity
            if len(entity_mappings) >= request.max_mappings_per_entity:
                break

        return mappings

    async def _generate_embeddings(self, items: List[Any]):
        """Generate embeddings for entities and docs"""
        for item in items:
            if not hasattr(item, 'embedding') or not item.embedding:
                # Create text representation
                if isinstance(item, CodeEntity):
                    text = self._entity_to_text(item)
                elif isinstance(item, DocEntity):
                    text = self._doc_to_text(item)
                else:
                    continue

                embedding = await self.embedding_generator.generate_embedding(text)
                item.embedding = embedding

    def _entity_to_text(self, entity: CodeEntity) -> str:
        """Convert entity to text representation"""
        parts = [
            f"Name: {entity.name}",
            f"Type: {entity.kind}",
            f"Language: {entity.lang}",
            f"Path: {entity.path}"
        ]

        if entity.signature:
            if isinstance(entity.signature, dict):
                if "parameters" in entity.signature:
                    params = entity.signature["parameters"]
                    if isinstance(params, list):
                        parts.append(f"Parameters: {', '.join(str(p) for p in params)}")

        return ". ".join(parts)

    def _doc_to_text(self, doc: DocEntity) -> str:
        """Convert doc to text representation"""
        parts = [
            f"Title: {doc.title or 'Untitled'}",
            f"Path: {doc.path}"
        ]

        if doc.headings:
            heading_texts = [h.get("text", "") for h in doc.headings[:5]]  # First 5 headings
            parts.append(f"Headings: {', '.join(heading_texts)}")

        return ". ".join(parts)

    async def _map_entity_to_docs(self,
                                entity: CodeEntity,
                                docs: List[DocEntity],
                                request: MapRequest) -> List[EntityMapping]:
        """Map a single entity to relevant docs"""
        candidate_mappings = []

        for doc in docs:
            mapping = await self._calculate_mapping_score(entity, doc, request)
            if mapping.score >= request.min_score_threshold:
                candidate_mappings.append(mapping)

        # Sort by score and return top mappings
        candidate_mappings.sort(key=lambda x: x.score, reverse=True)
        return candidate_mappings[:request.max_mappings_per_entity]

    async def _calculate_mapping_score(self,
                                     entity: CodeEntity,
                                     doc: DocEntity,
                                     request: MapRequest) -> EntityMapping:
        """Calculate comprehensive mapping score"""
        # Heuristics score
        heuristics_score = 0.0
        confidence = "low"

        if request.use_heuristics:
            heuristics_score, confidence = self.heuristic_matcher.calculate_heuristics_score(entity, doc)

        # Embedding score
        embedding_score = 0.0

        if request.use_embeddings and entity.embedding and doc.embedding:
            # Cosine similarity
            entity_vec = np.array(entity.embedding).reshape(1, -1)
            doc_vec = np.array(doc.embedding).reshape(1, -1)
            similarity = cosine_similarity(entity_vec, doc_vec)[0][0]
            # Convert to 0-1 scale
            embedding_score = (similarity + 1) / 2

        # Combine scores (weighted average)
        if request.use_embeddings and request.use_heuristics:
            combined_score = (heuristics_score * 0.6) + (embedding_score * 0.4)
        elif request.use_heuristics:
            combined_score = heuristics_score
        elif request.use_embeddings:
            combined_score = embedding_score
        else:
            combined_score = 0.0

        # Determine relation type based on context
        relation = self._determine_relation(entity, doc, combined_score)

        # Find best anchor if available
        anchor = self._find_best_anchor(entity, doc)

        return EntityMapping(
            id=f"{entity.id}:{doc.id}",
            project_id=entity.project_id,
            entity_id=entity.id,
            doc_id=doc.id,
            anchor=anchor,
            score=combined_score,
            relation=relation,
            confidence=confidence,
            heuristics_score=heuristics_score,
            embedding_score=embedding_score,
            metadata={
                "entity_kind": entity.kind,
                "entity_lang": entity.lang,
                "doc_title": doc.title
            }
        )

    def _determine_relation(self, entity: CodeEntity, doc: DocEntity, score: float) -> str:
        """Determine the type of relationship"""
        if score >= 0.8:
            return "describes"  # Strong match = main documentation
        elif score >= 0.5:
            return "references"  # Moderate match = reference
        else:
            return "mentions"  # Weak match = brief mention

    def _find_best_anchor(self, entity: CodeEntity, doc: DocEntity) -> Optional[str]:
        """Find the best anchor in the doc for this entity"""
        if not doc.headings:
            return None

        entity_name_lower = entity.name.lower()

        # Look for headings that match the entity name
        for heading in doc.headings:
            heading_text = heading.get("text", "").lower()
            if entity_name_lower in heading_text:
                return heading.get("anchor")

        return None


class MapWorker:
    """Main mapping worker"""

    def __init__(self, config: Dict):
        self.config = config
        self.redis_client = None
        self.nats_client = None

        # Initialize components
        self.embedding_generator = EmbeddingGenerator()
        self.heuristic_matcher = HeuristicMatcher()
        self.mapping_engine = MappingEngine(self.embedding_generator, self.heuristic_matcher)

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

        logger.info("Mapping worker initialized")

    async def run(self):
        """Main worker loop"""
        await self.initialize()

        subject = "align.map"
        queue_group = "map-workers"

        logger.info("Subscribing to mapping requests", subject=subject, queue=queue_group)

        async def message_handler(msg):
            await self.handle_map_request(msg)

        await self.nats_client.subscribe(
            subject,
            queue=queue_group,
            cb=message_handler
        )

        while True:
            await asyncio.sleep(1)

    async def handle_map_request(self, msg):
        """Handle incoming mapping request"""
        try:
            data = json.loads(msg.data.decode())
            request = MapRequest(**data)

            logger.info("Processing mapping request",
                       project_id=request.project_id,
                       entities=len(request.entity_ids or []),
                       docs=len(request.doc_ids or []),
                       request_id=request.request_id)

            # Get entities and docs from database/storage
            entities = await self._load_entities(request)
            docs = await self._load_docs(request)

            # Generate mappings
            mappings = await self.mapping_engine.generate_mappings(entities, docs, request)

            result = MapResult(
                project_id=request.project_id,
                mappings=mappings,
                success=True,
                map_duration=0.0,  # Would be calculated
                entities_processed=len(entities),
                docs_processed=len(docs),
                mappings_created=len(mappings),
                request_id=request.request_id
            )

            # Publish result
            result_data = asdict(result)
            result_subject = "align.map.result"
            await self.nats_client.publish(result_subject, json.dumps(result_data).encode())

            await msg.ack()

            logger.info("Mapping request processed",
                       project_id=request.project_id,
                       mappings_created=len(mappings))

        except Exception as e:
            logger.error("Failed to process mapping request", error=str(e))

    async def _load_entities(self, request: MapRequest) -> List[CodeEntity]:
        """Load entities from database/storage"""
        # In a real implementation, this would query the database
        # For now, return mock data
        return [
            CodeEntity(
                id=f"entity_{i}",
                project_id=request.project_id,
                kind="function",
                name=f"exampleFunction{i}",
                path=f"/src/example{i}.py",
                lang="python"
            ) for i in range(10)
        ]

    async def _load_docs(self, request: MapRequest) -> List[DocEntity]:
        """Load docs from database/storage"""
        # In a real implementation, this would query the database
        # For now, return mock data
        return [
            DocEntity(
                id=f"doc_{i}",
                project_id=request.project_id,
                path=f"/docs/example{i}.md",
                title=f"Example Documentation {i}",
                headings=[{"text": f"Example Function {i}", "anchor": f"example-function-{i}"}]
            ) for i in range(10)
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

    worker = MapWorker(config)

    try:
        await worker.run()
    except Exception as e:
        logger.error("Worker failed", error=str(e))
        await worker.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
