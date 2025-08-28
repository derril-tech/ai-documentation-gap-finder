#!/usr/bin/env python3
"""
AI Documentation Gap Finder - Scoring Worker

Calculates comprehensive quality metrics for documentation including:
- Readability scores (Flesch-Kincaid, SMOG, etc.)
- Completeness (entity coverage, section completeness)
- Freshness (age, update frequency, version alignment)
- Example density (code snippet coverage, runnable examples)

Features:
- Multiple readability algorithms
- Coverage analysis against code entities
- Temporal analysis with version tracking
- Priority scoring for gap identification
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

import aiofiles
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
class ReadabilityScores:
    """Readability assessment scores"""
    flesch_reading_ease: float = 0.0
    flesch_kincaid_grade: float = 0.0
    smog_index: float = 0.0
    coleman_liau_index: float = 0.0
    automated_readability_index: float = 0.0
    dale_chall_readability_score: float = 0.0
    linsear_write_formula: float = 0.0
    gunning_fog: float = 0.0
    composite_score: float = 0.0  # 0-1 scale


@dataclass
class CompletenessScores:
    """Documentation completeness metrics"""
    entity_coverage: float = 0.0  # % of entities documented
    section_completeness: float = 0.0  # % of expected sections present
    api_coverage: float = 0.0  # % of API endpoints documented
    parameter_coverage: float = 0.0  # % of parameters documented
    example_coverage: float = 0.0  # % of operations with examples
    composite_score: float = 0.0  # 0-1 scale


@dataclass
class FreshnessScores:
    """Documentation freshness metrics"""
    age_days: int = 0
    last_update_days: int = 0
    version_alignment: float = 0.0  # How well docs match current version
    update_frequency: float = 0.0  # Updates per month
    staleness_score: float = 0.0  # 0-1 scale (lower is fresher)
    composite_score: float = 0.0  # 0-1 scale


@dataclass
class ExampleDensityScores:
    """Code example quality and density metrics"""
    code_block_count: int = 0
    runnable_examples: int = 0
    example_languages: List[str] = None
    example_completeness: float = 0.0  # % of examples that are complete
    language_diversity: float = 0.0  # Variety of example languages
    snippet_quality: float = 0.0  # Average quality score of snippets
    composite_score: float = 0.0  # 0-1 scale


@dataclass
class DocScore:
    """Comprehensive documentation score"""
    id: str
    project_id: str
    doc_path: str
    readability: ReadabilityScores
    completeness: CompletenessScores
    freshness: FreshnessScores
    example_density: ExampleDensityScores
    overall_score: float = 0.0  # Weighted composite
    priority_score: float = 0.0  # For gap prioritization
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ScoreRequest:
    """Scoring request"""
    project_id: str
    doc_ids: List[str] = None
    entity_ids: List[str] = None
    include_readability: bool = True
    include_completeness: bool = True
    include_freshness: bool = True
    include_examples: bool = True
    priority_weights: Optional[Dict[str, float]] = None
    request_id: str = ""


@dataclass
class ScoreResult:
    """Scoring result"""
    project_id: str
    scores: List[DocScore]
    success: bool
    error_message: Optional[str] = None
    scoring_duration: float = 0.0
    docs_scored: int = 0
    request_id: str = ""


class ReadabilityAnalyzer:
    """Analyzes text readability using multiple algorithms"""

    def __init__(self):
        # Syllable counting patterns
        self.vowel_pattern = re.compile(r'[aeiouy]+', re.IGNORECASE)
        self.dipthong_pattern = re.compile(r'(ou|ie|oe|ea|ua|ia|ua)', re.IGNORECASE)

        # Word complexity patterns
        self.complex_word_pattern = re.compile(r'\b\w{7,}\b')

        # Sentence detection
        self.sentence_pattern = re.compile(r'[.!?]+')

    def analyze_text(self, text: str) -> ReadabilityScores:
        """Calculate all readability scores for text"""
        if not text or len(text.strip()) == 0:
            return ReadabilityScores()

        # Basic text statistics
        words = self._tokenize_words(text)
        sentences = self._tokenize_sentences(text)
        syllables = sum(self._count_syllables(word) for word in words)
        complex_words = len([w for w in words if len(w) >= 7])

        if len(sentences) == 0 or len(words) == 0:
            return ReadabilityScores()

        # Calculate individual scores
        flesch_ease = self._flesch_reading_ease(words, sentences, syllables)
        flesch_grade = self._flesch_kincaid_grade(words, sentences, syllables)
        smog = self._smog_index(sentences, complex_words)
        coleman = self._coleman_liau_index(words, sentences)
        ari = self._automated_readability_index(words, sentences, characters=len(text))
        dale_chall = self._dale_chall_readability_score(words, sentences)
        linsear = self._linsear_write_formula(words, sentences)
        fog = self._gunning_fog(words, sentences, complex_words)

        # Normalize scores to 0-1 scale (higher is better)
        scores = ReadabilityScores(
            flesch_reading_ease=self._normalize_flesch_ease(flesch_ease),
            flesch_kincaid_grade=self._normalize_grade_level(flesch_grade),
            smog_index=self._normalize_grade_level(smog),
            coleman_liau_index=self._normalize_grade_level(coleman),
            automated_readability_index=self._normalize_grade_level(ari),
            dale_chall_readability_score=self._normalize_dale_chall(dale_chall),
            linsear_write_formula=self._normalize_grade_level(linsear),
            gunning_fog=self._normalize_grade_level(fog)
        )

        # Calculate composite score
        scores.composite_score = self._calculate_composite_readability(scores)

        return scores

    def _tokenize_words(self, text: str) -> List[str]:
        """Tokenize text into words"""
        return re.findall(r'\b\w+\b', text.lower())

    def _tokenize_sentences(self, text: str) -> List[str]:
        """Tokenize text into sentences"""
        sentences = self.sentence_pattern.split(text)
        return [s.strip() for s in sentences if s.strip()]

    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word"""
        word = word.lower()
        count = len(self.vowel_pattern.findall(word))

        # Adjust for dipthongs and silent 'e'
        if word.endswith('e') and not word.endswith('le'):
            count -= 1
        if count == 0:
            count = 1

        return max(1, count)

    def _flesch_reading_ease(self, words: List[str], sentences: List[str], syllables: int) -> float:
        """Calculate Flesch Reading Ease score"""
        if len(sentences) == 0 or len(words) == 0:
            return 0
        return 206.835 - 1.015 * (len(words) / len(sentences)) - 84.6 * (syllables / len(words))

    def _flesch_kincaid_grade(self, words: List[str], sentences: List[str], syllables: int) -> float:
        """Calculate Flesch-Kincaid Grade Level"""
        if len(sentences) == 0 or len(words) == 0:
            return 0
        return 0.39 * (len(words) / len(sentences)) + 11.8 * (syllables / len(words)) - 15.59

    def _smog_index(self, sentences: List[str], complex_words: int) -> float:
        """Calculate SMOG Index"""
        if len(sentences) < 3:
            return 0
        return 1.043 * math.sqrt(complex_words * (30 / len(sentences))) + 3.1291

    def _coleman_liau_index(self, words: List[str], sentences: List[str]) -> float:
        """Calculate Coleman-Liau Index"""
        if len(sentences) == 0 or len(words) == 0:
            return 0
        chars = sum(len(word) for word in words)
        return 0.0588 * (chars / len(words) * 100) - 0.296 * (len(sentences) / len(words) * 100) - 15.8

    def _automated_readability_index(self, words: List[str], sentences: List[str], characters: int) -> float:
        """Calculate Automated Readability Index"""
        if len(sentences) == 0 or len(words) == 0:
            return 0
        return 4.71 * (characters / len(words)) + 0.5 * (len(words) / len(sentences)) - 21.43

    def _dale_chall_readability_score(self, words: List[str], sentences: List[str]) -> float:
        """Calculate Dale-Chall Readability Score"""
        if len(sentences) == 0 or len(words) == 0:
            return 0
        # Simplified version - in practice would use Dale-Chall word list
        return 64 - 0.95 * (len(words) / len(sentences)) - 0.69 * (len(words) / len(sentences))

    def _linsear_write_formula(self, words: List[str], sentences: List[str]) -> float:
        """Calculate Linsear Write Formula"""
        if len(sentences) == 0 or len(words) == 0:
            return 0
        return (len(words) / len(sentences) + len([w for w in words if len(w) > 6]) * 3) / len(sentences)

    def _gunning_fog(self, words: List[str], sentences: List[str], complex_words: int) -> float:
        """Calculate Gunning Fog Index"""
        if len(sentences) == 0 or len(words) == 0:
            return 0
        return 0.4 * ((len(words) / len(sentences)) + 100 * (complex_words / len(words)))

    def _normalize_flesch_ease(self, score: float) -> float:
        """Normalize Flesch Reading Ease to 0-1 scale"""
        # Flesch scores range from ~0-120, higher is easier
        return max(0, min(1, score / 100))

    def _normalize_grade_level(self, grade: float) -> float:
        """Normalize grade level to 0-1 scale (lower grades are better)"""
        # Assuming college level (13) is the target, anything above is penalized
        if grade <= 13:
            return 1 - (grade / 13)
        else:
            return max(0, 1 - ((grade - 13) / 10))

    def _normalize_dale_chall(self, score: float) -> float:
        """Normalize Dale-Chall score to 0-1 scale"""
        # Dale-Chall ranges from 0-10, lower is better
        return max(0, min(1, 1 - (score / 10)))

    def _calculate_composite_readability(self, scores: ReadabilityScores) -> float:
        """Calculate composite readability score"""
        # Weight different metrics
        weights = {
            'flesch_reading_ease': 0.3,
            'flesch_kincaid_grade': 0.2,
            'smog_index': 0.15,
            'coleman_liau_index': 0.15,
            'automated_readability_index': 0.1,
            'dale_chall_readability_score': 0.05,
            'linsear_write_formula': 0.025,
            'gunning_fog': 0.025
        }

        weighted_sum = sum(getattr(scores, metric) * weight for metric, weight in weights.items())
        return weighted_sum


class CompletenessAnalyzer:
    """Analyzes documentation completeness"""

    def __init__(self):
        self.required_sections = {
            'overview', 'getting_started', 'api_reference', 'examples',
            'troubleshooting', 'changelog'
        }

    def analyze_doc(self, doc: Dict, entities: List[Dict], mappings: List[Dict]) -> CompletenessScores:
        """Analyze completeness of documentation"""
        scores = CompletenessScores()

        # Entity coverage
        if entities:
            mapped_entities = set(m['entity_id'] for m in mappings if m.get('doc_id') == doc.get('id', ''))
            scores.entity_coverage = len(mapped_entities) / len(entities)

        # Section completeness
        headings = doc.get('headings', [])
        heading_texts = [h.get('text', '').lower() for h in headings]
        found_sections = set()

        for section in self.required_sections:
            if any(section.replace('_', ' ') in text for text in heading_texts):
                found_sections.add(section)

        scores.section_completeness = len(found_sections) / len(self.required_sections)

        # API coverage (simplified)
        api_entities = [e for e in entities if e.get('kind') == 'endpoint']
        if api_entities:
            documented_apis = len([e for e in api_entities if any(m.get('entity_id') == e['id'] for m in mappings)])
            scores.api_coverage = documented_apis / len(api_entities)

        # Example coverage
        code_blocks = doc.get('code_blocks', [])
        total_operations = len(api_entities) if api_entities else len(entities)
        if total_operations > 0:
            scores.example_coverage = min(1.0, len(code_blocks) / total_operations)

        # Calculate composite
        scores.composite_score = (
            scores.entity_coverage * 0.4 +
            scores.section_completeness * 0.3 +
            scores.api_coverage * 0.2 +
            scores.example_coverage * 0.1
        )

        return scores


class FreshnessAnalyzer:
    """Analyzes documentation freshness"""

    def analyze_doc(self, doc: Dict, project_version: Optional[str] = None) -> FreshnessScores:
        """Analyze freshness of documentation"""
        scores = FreshnessScores()

        # Calculate age
        last_updated = doc.get('last_updated')
        if last_updated:
            if isinstance(last_updated, str):
                last_updated = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            elif isinstance(last_updated, (int, float)):
                last_updated = datetime.fromtimestamp(last_updated)

            if isinstance(last_updated, datetime):
                now = datetime.now()
                scores.age_days = (now - last_updated).days
                scores.last_update_days = scores.age_days

        # Version alignment (simplified)
        doc_version = self._extract_version_from_doc(doc)
        if project_version and doc_version:
            scores.version_alignment = 1.0 if doc_version == project_version else 0.5

        # Staleness score (inverse of freshness)
        if scores.age_days > 0:
            # Exponential decay - docs older than 90 days get penalized
            scores.staleness_score = min(1.0, scores.age_days / 365)
        else:
            scores.staleness_score = 0.0

        # Composite score (higher is fresher)
        scores.composite_score = 1.0 - scores.staleness_score

        return scores

    def _extract_version_from_doc(self, doc: Dict) -> Optional[str]:
        """Extract version information from document"""
        # Look in frontmatter
        frontmatter = doc.get('frontmatter', {})
        if 'version' in frontmatter:
            return frontmatter['version']

        # Look in headings
        headings = doc.get('headings', [])
        for heading in headings:
            text = heading.get('text', '').lower()
            if 'version' in text:
                # Extract version number
                version_match = re.search(r'version\s*(\d+\.\d+)', text, re.IGNORECASE)
                if version_match:
                    return version_match.group(1)

        return None


class ExampleDensityAnalyzer:
    """Analyzes code example quality and density"""

    def analyze_doc(self, doc: Dict) -> ExampleDensityScores:
        """Analyze example density and quality"""
        scores = ExampleDensityScores()

        code_blocks = doc.get('code_blocks', [])
        scores.code_block_count = len(code_blocks)

        if not code_blocks:
            return scores

        # Analyze languages
        languages = set()
        runnable_count = 0

        for block in code_blocks:
            lang = block.get('language', '').lower()
            if lang:
                languages.add(lang)

            # Check if runnable (has complete structure)
            code = block.get('code', '')
            if self._is_runnable_example(code, lang):
                runnable_count += 1

        scores.runnable_examples = runnable_count
        scores.example_languages = list(languages)

        # Language diversity
        scores.language_diversity = min(1.0, len(languages) / 5)  # Max diversity at 5 languages

        # Completeness
        scores.example_completeness = runnable_count / len(code_blocks)

        # Snippet quality (simplified)
        total_quality = 0
        for block in code_blocks:
            total_quality += self._assess_snippet_quality(block)
        scores.snippet_quality = total_quality / len(code_blocks)

        # Composite score
        scores.composite_score = (
            scores.example_completeness * 0.4 +
            scores.language_diversity * 0.3 +
            scores.snippet_quality * 0.3
        )

        return scores

    def _is_runnable_example(self, code: str, language: str) -> bool:
        """Check if code example appears runnable"""
        if not code or len(code.strip()) < 10:
            return False

        # Language-specific checks
        if language in ['python', 'py']:
            return 'def ' in code or 'import ' in code or 'print(' in code
        elif language in ['javascript', 'js', 'typescript', 'ts']:
            return 'function' in code or 'const ' in code or 'let ' in code
        elif language in ['bash', 'shell', 'sh']:
            return code.strip().startswith(('#!/bin', 'echo ', 'ls ', 'cd '))
        else:
            return len(code.split('\n')) > 3  # Multi-line examples are likely runnable

    def _assess_snippet_quality(self, block: Dict) -> float:
        """Assess quality of a code snippet"""
        code = block.get('code', '')
        if not code:
            return 0.0

        score = 0.0

        # Length check
        lines = code.split('\n')
        if 3 <= len(lines) <= 50:
            score += 0.3

        # Has comments
        if '#' in code or '//' in code or '/*' in code:
            score += 0.2

        # Has meaningful content (not just print statements)
        if any(keyword in code.lower() for keyword in ['class', 'function', 'def', 'import', 'const']):
            score += 0.3

        # Proper formatting
        if not code.startswith(' ') and not '\t' in code:
            score += 0.2

        return min(1.0, score)


class ScoringEngine:
    """Main scoring engine"""

    def __init__(self):
        self.readability_analyzer = ReadabilityAnalyzer()
        self.completeness_analyzer = CompletenessAnalyzer()
        self.freshness_analyzer = FreshnessAnalyzer()
        self.example_analyzer = ExampleDensityAnalyzer()

    async def score_documentation(self,
                                docs: List[Dict],
                                entities: List[Dict],
                                mappings: List[Dict],
                                request: ScoreRequest) -> List[DocScore]:
        """Score documentation comprehensively"""
        scored_docs = []

        for doc in docs:
            doc_score = await self._score_single_doc(doc, entities, mappings, request)
            scored_docs.append(doc_score)

        return scored_docs

    async def _score_single_doc(self,
                              doc: Dict,
                              entities: List[Dict],
                              mappings: List[Dict],
                              request: ScoreRequest) -> DocScore:
        """Score a single document"""
        doc_id = doc.get('id', '')
        project_id = doc.get('project_id', '')

        # Extract text content
        text_content = self._extract_text_content(doc)

        # Calculate individual scores
        readability = ReadabilityScores()
        if request.include_readability and text_content:
            readability = self.readability_analyzer.analyze_text(text_content)

        completeness = CompletenessScores()
        if request.include_completeness:
            completeness = self.completeness_analyzer.analyze_doc(doc, entities, mappings)

        freshness = FreshnessScores()
        if request.include_freshness:
            freshness = self.freshness_analyzer.analyze_doc(doc)

        example_density = ExampleDensityScores()
        if request.include_examples:
            example_density = self.example_analyzer.analyze_doc(doc)

        # Calculate overall score
        overall_score = self._calculate_overall_score(
            readability, completeness, freshness, example_density, request
        )

        # Calculate priority score for gap identification
        priority_score = self._calculate_priority_score(
            readability, completeness, freshness, example_density, request
        )

        return DocScore(
            id=f"score_{doc_id}",
            project_id=project_id,
            doc_path=doc.get('path', ''),
            readability=readability,
            completeness=completeness,
            freshness=freshness,
            example_density=example_density,
            overall_score=overall_score,
            priority_score=priority_score,
            metadata={
                'word_count': doc.get('word_count', 0),
                'heading_count': len(doc.get('headings', [])),
                'link_count': len(doc.get('links', [])),
                'code_block_count': len(doc.get('code_blocks', []))
            }
        )

    def _extract_text_content(self, doc: Dict) -> str:
        """Extract readable text content from document"""
        content_parts = []

        # Add title
        if doc.get('title'):
            content_parts.append(doc['title'])

        # Add headings
        for heading in doc.get('headings', []):
            content_parts.append(heading.get('text', ''))

        # Add code blocks (without the code itself, just descriptions)
        for block in doc.get('code_blocks', []):
            if block.get('language'):
                content_parts.append(f"Example in {block['language']}")

        # This is simplified - in practice would extract more text
        return ' '.join(content_parts)

    def _calculate_overall_score(self,
                               readability: ReadabilityScores,
                               completeness: CompletenessScores,
                               freshness: FreshnessScores,
                               example_density: ExampleDensityScores,
                               request: ScoreRequest) -> float:
        """Calculate overall documentation score"""
        weights = {
            'readability': 0.25,
            'completeness': 0.35,
            'freshness': 0.25,
            'example_density': 0.15
        }

        score = (
            readability.composite_score * weights['readability'] +
            completeness.composite_score * weights['completeness'] +
            freshness.composite_score * weights['freshness'] +
            example_density.composite_score * weights['example_density']
        )

        return max(0.0, min(1.0, score))

    def _calculate_priority_score(self,
                                readability: ReadabilityScores,
                                completeness: CompletenessScores,
                                freshness: FreshnessScores,
                                example_density: ExampleDensityScores,
                                request: ScoreRequest) -> float:
        """Calculate priority score for gap identification"""
        # Use custom weights if provided
        weights = request.priority_weights or {
            'readability': 0.2,
            'completeness': 0.4,  # Most important for gaps
            'freshness': 0.3,
            'example_density': 0.1
        }

        # Calculate gaps (inverse of scores)
        readability_gap = 1.0 - readability.composite_score
        completeness_gap = 1.0 - completeness.composite_score
        freshness_gap = 1.0 - freshness.composite_score
        example_gap = 1.0 - example_density.composite_score

        priority = (
            readability_gap * weights['readability'] +
            completeness_gap * weights['completeness'] +
            freshness_gap * weights['freshness'] +
            example_gap * weights['example_density']
        )

        return max(0.0, min(1.0, priority))


class ScoreWorker:
    """Main scoring worker"""

    def __init__(self, config: Dict):
        self.config = config
        self.redis_client = None
        self.nats_client = None
        self.scoring_engine = ScoringEngine()

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

        logger.info("Scoring worker initialized")

    async def run(self):
        """Main worker loop"""
        await self.initialize()

        subject = "docs.score"
        queue_group = "score-workers"

        logger.info("Subscribing to scoring requests", subject=subject, queue=queue_group)

        async def message_handler(msg):
            await self.handle_score_request(msg)

        await self.nats_client.subscribe(
            subject,
            queue=queue_group,
            cb=message_handler
        )

        while True:
            await asyncio.sleep(1)

    async def handle_score_request(self, msg):
        """Handle incoming scoring request"""
        try:
            data = json.loads(msg.data.decode())
            request = ScoreRequest(**data)

            logger.info("Processing scoring request",
                       project_id=request.project_id,
                       docs=len(request.doc_ids or []),
                       request_id=request.request_id)

            start_time = time.time()

            # Load docs, entities, and mappings
            docs = await self._load_docs(request)
            entities = await self._load_entities(request)
            mappings = await self._load_mappings(request)

            # Score documentation
            scores = await self.scoring_engine.score_documentation(docs, entities, mappings, request)

            duration = time.time() - start_time

            result = ScoreResult(
                project_id=request.project_id,
                scores=scores,
                success=True,
                scoring_duration=duration,
                docs_scored=len(scores),
                request_id=request.request_id
            )

            # Publish result
            result_data = asdict(result)
            result_subject = "docs.score.result"
            await self.nats_client.publish(result_subject, json.dumps(result_data).encode())

            await msg.ack()

            logger.info("Scoring request processed",
                       project_id=request.project_id,
                       docs_scored=len(scores),
                       duration=duration)

        except Exception as e:
            logger.error("Failed to process scoring request", error=str(e))

    async def _load_docs(self, request: ScoreRequest) -> List[Dict]:
        """Load docs from database/storage"""
        # Mock implementation
        return [
            {
                'id': doc_id,
                'project_id': request.project_id,
                'path': f'/docs/example_{i}.md',
                'title': f'Example Documentation {i}',
                'headings': [{'text': f'Heading {j}', 'level': 2} for j in range(3)],
                'code_blocks': [{'language': 'python', 'code': f'print("example {i}")'}],
                'word_count': 500 + i * 100,
                'last_updated': time.time() - i * 86400  # Days ago
            } for i, doc_id in enumerate(request.doc_ids or ['doc_1', 'doc_2', 'doc_3'])
        ]

    async def _load_entities(self, request: ScoreRequest) -> List[Dict]:
        """Load entities from database/storage"""
        # Mock implementation
        return [
            {
                'id': f'entity_{i}',
                'kind': 'function',
                'name': f'exampleFunction{i}',
                'signature': {'parameters': []}
            } for i in range(10)
        ]

    async def _load_mappings(self, request: ScoreRequest) -> List[Dict]:
        """Load mappings from database/storage"""
        # Mock implementation
        return [
            {
                'entity_id': f'entity_{i}',
                'doc_id': f'doc_{(i % 3) + 1}',
                'score': 0.8 - i * 0.05
            } for i in range(7)
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

    worker = ScoreWorker(config)

    try:
        await worker.run()
    except Exception as e:
        logger.error("Worker failed", error=str(e))
        await worker.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
