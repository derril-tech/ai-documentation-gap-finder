#!/usr/bin/env python3
"""
AI Documentation Gap Finder - Telemetry Worker

Collects and analyzes usage patterns to inform documentation prioritization:
- API endpoint usage tracking and frequency analysis
- Documentation 404 error monitoring and gap identification
- Search query analysis and not-found pattern detection
- User behavior insights for content optimization

Features:
- Real-time telemetry ingestion from various sources
- Pattern analysis and trend identification
- Gap prioritization based on usage data
- Integration with existing scoring and mapping systems
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse, parse_qs

import aiofiles
import httpx
from nats.aio.client import Client as NATS
from nats.aio.errors import ErrTimeout
import redis.asyncio as redis
import structlog
from collections import defaultdict, Counter

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
class EndpointUsageEvent:
    """API endpoint usage event"""
    id: str
    project_id: str
    endpoint: str
    method: str
    status_code: int
    response_time: float
    user_agent: str
    ip_address: str
    timestamp: float
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    request_size: Optional[int] = None
    response_size: Optional[int] = None
    error_message: Optional[str] = None


@dataclass
class Doc404Event:
    """Documentation 404 event"""
    id: str
    project_id: str
    requested_path: str
    referrer: Optional[str]
    user_agent: str
    ip_address: str
    timestamp: float
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    query_params: Optional[Dict[str, List[str]]] = None
    potential_matches: Optional[List[str]] = None


@dataclass
class SearchEvent:
    """Search query event"""
    id: str
    project_id: str
    query: str
    results_count: int
    clicked_result: Optional[str] = None
    user_agent: str
    ip_address: str
    timestamp: float
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    session_id: Optional[str] = None
    search_type: str = "documentation"  # documentation, api, code
    filters_applied: Optional[Dict[str, Any]] = None


@dataclass
class TelemetryAnalysis:
    """Telemetry analysis results"""
    project_id: str
    period_start: float
    period_end: float
    endpoint_usage: Dict[str, Dict[str, Any]]
    doc_404_patterns: List[Dict[str, Any]]
    search_patterns: List[Dict[str, Any]]
    prioritized_gaps: List[Dict[str, Any]]
    recommendations: List[str]
    analysis_timestamp: float


@dataclass
class TelemetryRequest:
    """Telemetry analysis request"""
    project_id: str
    analysis_type: str = "comprehensive"  # comprehensive, endpoint, search, 404
    time_range_hours: int = 24
    include_historical: bool = False
    request_id: str = ""


class TelemetryCollector:
    """Collects and processes telemetry events"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.endpoint_key_prefix = "telemetry:endpoint:"
        self.doc404_key_prefix = "telemetry:doc404:"
        self.search_key_prefix = "telemetry:search:"
        self.analysis_key_prefix = "telemetry:analysis:"

    async def record_endpoint_usage(self, event: EndpointUsageEvent):
        """Record API endpoint usage"""
        key = f"{self.endpoint_key_prefix}{event.project_id}:{event.endpoint}:{event.method}"

        # Store individual event
        event_data = asdict(event)
        await self.redis.lpush(f"{key}:events", json.dumps(event_data))
        await self.redis.ltrim(f"{key}:events", 0, 999)  # Keep last 1000 events

        # Update aggregates
        await self.redis.hincrby(f"{key}:counts", str(event.status_code), 1)
        await self.redis.hincrbyfloat(f"{key}:response_times", "total", event.response_time)
        await self.redis.hincrby(f"{key}:response_times", "count", 1)

        # Update rolling window (last 24 hours)
        window_key = f"{key}:window:{int(time.time() / 3600)}"  # Hourly windows
        await self.redis.hincrby(window_key, str(event.status_code), 1)
        await self.redis.expire(window_key, 86400)  # Expire after 24 hours

        logger.debug("Recorded endpoint usage", endpoint=event.endpoint, method=event.method)

    async def record_doc_404(self, event: Doc404Event):
        """Record documentation 404 event"""
        key = f"{self.doc404_key_prefix}{event.project_id}"

        # Store individual event
        event_data = asdict(event)
        await self.redis.lpush(f"{key}:events", json.dumps(event_data))
        await self.redis.ltrim(f"{key}:events", 0, 999)

        # Update path frequency
        await self.redis.zincrby(f"{key}:paths", 1, event.requested_path)

        # Update referrer analysis
        if event.referrer:
            await self.redis.zincrby(f"{key}:referrers", 1, event.referrer)

        # Update hourly window
        hour_key = f"{key}:hourly:{int(time.time() / 3600)}"
        await self.redis.hincrby(hour_key, event.requested_path, 1)
        await self.redis.expire(hour_key, 86400)

        logger.debug("Recorded doc 404", path=event.requested_path, referrer=event.referrer)

    async def record_search_event(self, event: SearchEvent):
        """Record search event"""
        key = f"{self.search_key_prefix}{event.project_id}"

        # Store individual event
        event_data = asdict(event)
        await self.redis.lpush(f"{key}:events", json.dumps(event_data))
        await self.redis.ltrim(f"{key}:events", 0, 999)

        # Update query frequency
        await self.redis.zincrby(f"{key}:queries", 1, event.query)

        # Update zero-results queries
        if event.results_count == 0:
            await self.redis.zincrby(f"{key}:zero_results", 1, event.query)

        # Update result click patterns
        if event.clicked_result:
            click_key = f"{key}:clicks:{event.query}"
            await self.redis.zincrby(click_key, 1, event.clicked_result)

        logger.debug("Recorded search event", query=event.query, results=event.results_count)

    async def get_endpoint_usage_stats(self, project_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get endpoint usage statistics"""
        pattern = f"{self.endpoint_key_prefix}{project_id}:*"
        endpoint_keys = await self.redis.keys(pattern)

        stats = {}
        cutoff_time = time.time() - (hours * 3600)

        for key in endpoint_keys:
            if ":events" not in key:
                continue

            base_key = key.replace(":events", "")
            events_data = await self.redis.lrange(key, 0, -1)

            total_requests = 0
            status_counts = defaultdict(int)
            response_times = []
            error_count = 0

            for event_json in events_data:
                try:
                    event = json.loads(event_json)
                    if event['timestamp'] > cutoff_time:
                        total_requests += 1
                        status_counts[event['status_code']] += 1
                        response_times.append(event['response_time'])

                        if event['status_code'] >= 400:
                            error_count += 1
                except json.JSONDecodeError:
                    continue

            if total_requests > 0:
                endpoint_path = base_key.replace(f"{self.endpoint_key_prefix}{project_id}:", "")
                stats[endpoint_path] = {
                    'total_requests': total_requests,
                    'status_counts': dict(status_counts),
                    'avg_response_time': sum(response_times) / len(response_times),
                    'error_rate': error_count / total_requests,
                    'p95_response_time': sorted(response_times)[int(len(response_times) * 0.95)] if response_times else 0
                }

        return stats

    async def get_doc_404_patterns(self, project_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get documentation 404 patterns"""
        key = f"{self.doc404_key_prefix}{project_id}"
        paths_key = f"{key}:paths"

        # Get top 404 paths
        top_paths = await self.redis.zrevrange(paths_key, 0, 19, withscores=True)
        patterns = []

        for path, count in top_paths:
            # Get recent events for this path
            events_key = f"{key}:events"
            events_data = await self.redis.lrange(events_key, 0, -1)
            recent_events = []

            for event_json in events_data:
                try:
                    event = json.loads(event_json)
                    if event['requested_path'] == path.decode():
                        recent_events.append(event)
                        if len(recent_events) >= 10:  # Limit to 10 recent events
                            break
                except json.JSONDecodeError:
                    continue

            patterns.append({
                'path': path.decode(),
                'total_count': int(count),
                'recent_events': recent_events,
                'potential_solutions': self._suggest_404_solutions(path.decode())
            })

        return patterns

    async def get_search_patterns(self, project_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get search query patterns"""
        key = f"{self.search_key_prefix}{project_id}"
        queries_key = f"{key}:queries"
        zero_results_key = f"{key}:zero_results"

        # Get top queries
        top_queries = await self.redis.zrevrange(queries_key, 0, 19, withscores=True)
        zero_results_queries = await self.redis.zrevrange(zero_results_key, 0, 19, withscores=True)

        patterns = []
        zero_results_set = {q.decode() for q, _ in zero_results_queries}

        for query, count in top_queries:
            query_str = query.decode()
            is_zero_results = query_str in zero_results_set

            patterns.append({
                'query': query_str,
                'total_searches': int(count),
                'zero_results': is_zero_results,
                'suggested_improvements': self._suggest_search_improvements(query_str, is_zero_results)
            })

        return patterns

    def _suggest_404_solutions(self, path: str) -> List[str]:
        """Suggest solutions for 404 paths"""
        suggestions = []

        # Check for common patterns
        if path.endswith(('.html', '.htm')):
            suggestions.append("Convert HTML documentation to Markdown/MDX format")
        elif '/api/' in path:
            suggestions.append("Create API documentation for this endpoint")
        elif any(term in path.lower() for term in ['guide', 'tutorial', 'howto']):
            suggestions.append("Create comprehensive guide documentation")
        elif path.count('/') > 3:
            suggestions.append("Consider flattening documentation structure")

        # Generic suggestions
        suggestions.extend([
            "Add redirect from old URL to current documentation",
            "Create placeholder page explaining the missing content",
            "Add to documentation sitemap or index"
        ])

        return suggestions

    def _suggest_search_improvements(self, query: str, is_zero_results: bool) -> List[str]:
        """Suggest improvements for search queries"""
        suggestions = []

        if is_zero_results:
            suggestions.append("Consider adding documentation that covers this topic")
            suggestions.append("Add relevant keywords to existing documentation")
            suggestions.append("Create FAQ or troubleshooting section")

        if len(query.split()) > 5:
            suggestions.append("Consider simplifying complex queries")
            suggestions.append("Break down complex topics into separate documentation pages")

        if any(term in query.lower() for term in ['error', 'bug', 'issue', 'problem']):
            suggestions.append("Enhance troubleshooting and error handling documentation")

        return suggestions


class TelemetryAnalyzer:
    """Analyzes telemetry data to identify patterns and insights"""

    def __init__(self, collector: TelemetryCollector):
        self.collector = collector

    async def analyze_telemetry(self, request: TelemetryRequest) -> TelemetryAnalysis:
        """Perform comprehensive telemetry analysis"""
        analysis_start = time.time()

        # Gather data based on analysis type
        endpoint_usage = {}
        doc_404_patterns = []
        search_patterns = []

        if request.analysis_type in ['comprehensive', 'endpoint']:
            endpoint_usage = await self.collector.get_endpoint_usage_stats(
                request.project_id, request.time_range_hours
            )

        if request.analysis_type in ['comprehensive', '404']:
            doc_404_patterns = await self.collector.get_doc_404_patterns(
                request.project_id, request.time_range_hours
            )

        if request.analysis_type in ['comprehensive', 'search']:
            search_patterns = await self.collector.get_search_patterns(
                request.project_id, request.time_range_hours
            )

        # Generate prioritized gaps based on telemetry
        prioritized_gaps = self._prioritize_gaps_based_on_telemetry(
            endpoint_usage, doc_404_patterns, search_patterns
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            endpoint_usage, doc_404_patterns, search_patterns
        )

        analysis_end = time.time()

        return TelemetryAnalysis(
            project_id=request.project_id,
            period_start=time.time() - (request.time_range_hours * 3600),
            period_end=time.time(),
            endpoint_usage=endpoint_usage,
            doc_404_patterns=doc_404_patterns,
            search_patterns=search_patterns,
            prioritized_gaps=prioritized_gaps,
            recommendations=recommendations,
            analysis_timestamp=analysis_end
        )

    def _prioritize_gaps_based_on_telemetry(self,
                                           endpoint_usage: Dict,
                                           doc_404_patterns: List,
                                           search_patterns: List) -> List[Dict[str, Any]]:
        """Prioritize documentation gaps based on telemetry data"""
        prioritized_gaps = []

        # High-traffic endpoints without good documentation
        for endpoint, stats in endpoint_usage.items():
            if stats['error_rate'] > 0.1:  # High error rate
                prioritized_gaps.append({
                    'type': 'endpoint_errors',
                    'priority': 'high',
                    'endpoint': endpoint,
                    'error_rate': stats['error_rate'],
                    'reason': f"High error rate ({stats['error_rate']:.1%}) indicates poor documentation"
                })

        # Frequent 404s indicate missing content
        for pattern in doc_404_patterns[:10]:  # Top 10 patterns
            prioritized_gaps.append({
                'type': 'missing_content',
                'priority': 'high' if pattern['total_count'] > 50 else 'medium',
                'path': pattern['path'],
                'frequency': pattern['total_count'],
                'reason': f"Frequent 404s for {pattern['path']}"
            })

        # Zero-result searches indicate content gaps
        for pattern in search_patterns:
            if pattern['zero_results']:
                prioritized_gaps.append({
                    'type': 'search_gap',
                    'priority': 'medium',
                    'query': pattern['query'],
                    'frequency': pattern['total_searches'],
                    'reason': f"No search results for '{pattern['query']}'"
                })

        # Sort by priority and frequency
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        prioritized_gaps.sort(key=lambda x: (
            priority_order.get(x['priority'], 0),
            x.get('frequency', 0)
        ), reverse=True)

        return prioritized_gaps

    def _generate_recommendations(self,
                                endpoint_usage: Dict,
                                doc_404_patterns: List,
                                search_patterns: List) -> List[str]:
        """Generate recommendations based on telemetry analysis"""
        recommendations = []

        # Endpoint usage recommendations
        high_error_endpoints = [
            endpoint for endpoint, stats in endpoint_usage.items()
            if stats['error_rate'] > 0.05
        ]
        if high_error_endpoints:
            recommendations.append(
                f"Improve error handling documentation for {len(high_error_endpoints)} high-error endpoints"
            )

        # 404 pattern recommendations
        if len(doc_404_patterns) > 5:
            recommendations.append(
                "Consider restructuring documentation to reduce 404 errors"
            )

        # Search recommendations
        zero_result_queries = [p for p in search_patterns if p['zero_results']]
        if len(zero_result_queries) > 3:
            recommendations.append(
                "Add documentation for frequently searched terms with no results"
            )

        # General recommendations
        recommendations.extend([
            "Monitor API usage patterns to identify under-documented features",
            "Implement documentation analytics to track user engagement",
            "Set up automated alerts for high-error endpoints",
            "Create feedback mechanisms for documentation improvement",
            "Establish regular review cycles for documentation based on usage data"
        ])

        return recommendations


class TelemetryWorker:
    """Main telemetry worker"""

    def __init__(self, config: Dict):
        self.config = config
        self.redis_client = None
        self.nats_client = None

        # Initialize components
        self.collector = None
        self.analyzer = None

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

        # Initialize components with Redis
        self.collector = TelemetryCollector(self.redis_client)
        self.analyzer = TelemetryAnalyzer(self.collector)

        logger.info("Telemetry worker initialized")

    async def run(self):
        """Main worker loop"""
        await self.initialize()

        # Subscribe to multiple telemetry event types
        subjects = [
            "telemetry.endpoint.usage",
            "telemetry.doc.404",
            "telemetry.search.query",
            "telemetry.analysis.request"
        ]

        for subject in subjects:
            queue_group = f"telemetry-workers-{subject.split('.')[-1]}"

            logger.info("Subscribing to telemetry events", subject=subject, queue=queue_group)

            async def message_handler(msg):
                await self.handle_telemetry_event(msg, subject)

            await self.nats_client.subscribe(
                subject,
                queue=queue_group,
                cb=message_handler
            )

        while True:
            await asyncio.sleep(1)

    async def handle_telemetry_event(self, msg, subject: str):
        """Handle incoming telemetry events"""
        try:
            data = json.loads(msg.data.decode())

            if "endpoint.usage" in subject:
                event = EndpointUsageEvent(**data)
                await self.collector.record_endpoint_usage(event)
                logger.debug("Processed endpoint usage event", endpoint=event.endpoint)

            elif "doc.404" in subject:
                event = Doc404Event(**data)
                await self.collector.record_doc_404(event)
                logger.debug("Processed doc 404 event", path=event.requested_path)

            elif "search.query" in subject:
                event = SearchEvent(**data)
                await self.collector.record_search_event(event)
                logger.debug("Processed search event", query=event.query)

            elif "analysis.request" in subject:
                request = TelemetryRequest(**data)
                analysis = await self.analyzer.analyze_telemetry(request)

                # Publish analysis results
                result_data = asdict(analysis)
                result_subject = "telemetry.analysis.result"
                await self.nats_client.publish(result_subject, json.dumps(result_data).encode())

                logger.info("Completed telemetry analysis",
                           project_id=request.project_id,
                           analysis_type=request.analysis_type)

            await msg.ack()

        except Exception as e:
            logger.error("Failed to process telemetry event", error=str(e))

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

    worker = TelemetryWorker(config)

    try:
        await worker.run()
    except Exception as e:
        logger.error("Worker failed", error=str(e))
        await worker.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
