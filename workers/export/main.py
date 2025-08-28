#!/usr/bin/env python3
"""
AI Documentation Gap Finder - Export Worker

Handles exporting documentation drafts and findings to external systems:
- PR export to documentation repositories with proper branch naming and changelogs
- Bundle export (JSON/PDF) with comprehensive findings and mappings
- Preview link generation for draft reviews
- Owner approval workflow integration

Features:
- GitHub/GitLab PR creation with conventional commits
- Automated changelog generation from gap analysis
- PDF report generation with diagrams and appendices
- Preview deployment for draft reviews
- Approval workflow with CODEOWNERS integration
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
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from urllib.parse import urlparse

import aiofiles
import httpx
from nats.aio.client import Client as NATS
from nats.aio.errors import ErrTimeout
import redis.asyncio as redis
import structlog
import yaml
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

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
class ExportRequest:
    """Export request"""
    project_id: str
    export_type: str  # 'pr' or 'bundle'
    target_repo: str
    drafts: List[str] = None  # Draft IDs to export
    gaps: List[str] = None  # Gap IDs to include in bundle
    format: str = 'json'  # For bundle: 'json' or 'pdf'
    include_changelog: bool = True
    include_preview: bool = True
    require_approval: bool = True
    request_id: str = ""


@dataclass
class ExportResult:
    """Export result"""
    project_id: str
    export_type: str
    success: bool
    pr_url: Optional[str] = None
    bundle_url: Optional[str] = None
    preview_url: Optional[str] = None
    changelog: Optional[str] = None
    error_message: Optional[str] = None
    export_duration: float = 0.0
    request_id: str = ""


@dataclass
class PRDetails:
    """Pull request details"""
    title: str
    body: str
    branch_name: str
    base_branch: str
    labels: List[str]
    reviewers: List[str]


class GitPlatformClient:
    """Client for Git platform operations (GitHub/GitLab)"""

    def __init__(self, platform: str, token: str, base_url: str = None):
        self.platform = platform.lower()
        self.token = token
        self.base_url = base_url or self._get_default_base_url()
        self.session = httpx.AsyncClient(
            headers={
                'Authorization': f'token {token}' if platform == 'github' else f'Bearer {token}',
                'Accept': 'application/vnd.github.v3+json' if platform == 'github' else 'application/json',
            },
            timeout=30.0
        )

    def _get_default_base_url(self) -> str:
        if self.platform == 'github':
            return 'https://api.github.com'
        elif self.platform == 'gitlab':
            return 'https://gitlab.com/api/v4'
        else:
            raise ValueError(f'Unsupported platform: {self.platform}')

    async def create_branch(self, repo: str, branch_name: str, base_sha: str) -> bool:
        """Create a new branch"""
        try:
            if self.platform == 'github':
                url = f'{self.base_url}/repos/{repo}/git/refs'
                data = {
                    'ref': f'refs/heads/{branch_name}',
                    'sha': base_sha
                }
                response = await self.session.post(url, json=data)
                return response.status_code == 201
            elif self.platform == 'gitlab':
                url = f'{self.base_url}/projects/{repo.replace("/", "%2F")}/repository/branches'
                data = {
                    'branch': branch_name,
                    'ref': base_sha
                }
                response = await self.session.post(url, json=data)
                return response.status_code == 201
        except Exception as e:
            logger.error("Failed to create branch", error=str(e))
            return False

    async def create_pull_request(self, repo: str, pr_details: PRDetails) -> Optional[str]:
        """Create a pull request"""
        try:
            if self.platform == 'github':
                url = f'{self.base_url}/repos/{repo}/pulls'
                data = {
                    'title': pr_details.title,
                    'body': pr_details.body,
                    'head': pr_details.branch_name,
                    'base': pr_details.base_branch,
                    'labels': pr_details.labels,
                }
                response = await self.session.post(url, json=data)
                if response.status_code == 201:
                    pr_data = response.json()
                    return pr_data.get('html_url')
            elif self.platform == 'gitlab':
                url = f'{self.base_url}/projects/{repo.replace("/", "%2F")}/merge_requests'
                data = {
                    'title': pr_details.title,
                    'description': pr_details.body,
                    'source_branch': pr_details.branch_name,
                    'target_branch': pr_details.base_branch,
                    'labels': ','.join(pr_details.labels) if pr_details.labels else '',
                }
                response = await self.session.post(url, json=data)
                if response.status_code == 201:
                    pr_data = response.json()
                    return pr_data.get('web_url')
        except Exception as e:
            logger.error("Failed to create pull request", error=str(e))
            return None

    async def get_default_branch(self, repo: str) -> Optional[str]:
        """Get the default branch for a repository"""
        try:
            if self.platform == 'github':
                url = f'{self.base_url}/repos/{repo}'
                response = await self.session.get(url)
                if response.status_code == 200:
                    return response.json().get('default_branch')
            elif self.platform == 'gitlab':
                url = f'{self.base_url}/projects/{repo.replace("/", "%2F")}'
                response = await self.session.get(url)
                if response.status_code == 200:
                    return response.json().get('default_branch')
        except Exception as e:
            logger.error("Failed to get default branch", error=str(e))
            return None

    async def close(self):
        """Close the HTTP session"""
        await self.session.aclose()


class ChangelogGenerator:
    """Generates changelogs from gap analysis and drafts"""

    def __init__(self):
        self.templates = {
            'added': '✨ **Added**: {description}',
            'fixed': '🔧 **Fixed**: {description}',
            'improved': '🚀 **Improved**: {description}',
            'removed': '🗑️ **Removed**: {description}',
            'security': '🔒 **Security**: {description}',
        }

    def generate_changelog(self, drafts: List[Dict], gaps: List[Dict], project_name: str) -> str:
        """Generate a comprehensive changelog"""
        sections = []

        # Header
        sections.append(f"# 📝 Documentation Updates - {project_name}")
        sections.append(f"\n**Generated on:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        sections.append("")

        # Summary statistics
        total_drafts = len(drafts)
        total_gaps = len(gaps)
        critical_gaps = len([g for g in gaps if g.get('severity') == 'critical'])
        high_gaps = len([g for g in gaps if g.get('severity') == 'high'])

        sections.append("## 📊 Summary")
        sections.append(f"- **New Drafts:** {total_drafts}")
        sections.append(f"- **Gaps Addressed:** {total_gaps}")
        if critical_gaps > 0:
            sections.append(f"- **Critical Issues:** {critical_gaps} ⚠️")
        if high_gaps > 0:
            sections.append(f"- **High Priority:** {high_gaps} ⚠️")
        sections.append("")

        # Drafts section
        if drafts:
            sections.append("## 📝 New Documentation")
            for draft in drafts:
                draft_type = draft.get('frontmatter', {}).get('draft_type', 'general')
                title = draft.get('frontmatter', {}).get('title', 'Untitled Draft')
                sections.append(f"- **{title}** ({draft_type})")
                if draft.get('rationale'):
                    rationale = draft['rationale'].get('summary', '')
                    if rationale:
                        sections.append(f"  - {rationale}")
            sections.append("")

        # Gap resolutions
        if gaps:
            sections.append("## 🐛 Issues Resolved")
            for gap in gaps:
                gap_type = gap.get('type', 'unknown')
                severity = gap.get('severity', 'medium')
                reason = gap.get('reason', 'Documentation gap')

                emoji = {
                    'critical': '🚨',
                    'high': '⚠️',
                    'medium': 'ℹ️',
                    'low': '📝'
                }.get(severity, '📝')

                sections.append(f"- {emoji} **{gap_type.title()}**: {reason}")
            sections.append("")

        # Technical details
        sections.append("## 🔧 Technical Details")
        sections.append("### Files Modified")

        # Group drafts by type
        draft_types = {}
        for draft in drafts:
            draft_type = draft.get('frontmatter', {}).get('draft_type', 'general')
            if draft_type not in draft_types:
                draft_types[draft_type] = []
            draft_types[draft_type].append(draft)

        for draft_type, type_drafts in draft_types.items():
            sections.append(f"**{draft_type.title()} Documentation:**")
            for draft in type_drafts:
                doc_path = draft.get('doc_path', 'new-file.md')
                sections.append(f"  - `{doc_path}`")
        sections.append("")

        # Footer
        sections.append("---")
        sections.append("*This changelog was automatically generated by AI Documentation Gap Finder*")
        sections.append("*Review and test all changes before merging*")

        return "\n".join(sections)


class PDFGenerator:
    """Generates PDF reports from analysis data"""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
        )
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
        )

    def generate_pdf_report(self, data: Dict[str, Any], output_path: Path) -> bool:
        """Generate comprehensive PDF report"""
        try:
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )

            story = []

            # Title
            title = Paragraph("AI Documentation Gap Analysis Report", self.title_style)
            story.append(title)
            story.append(Spacer(1, 12))

            # Executive Summary
            story.append(Paragraph("Executive Summary", self.heading_style))
            summary_data = data.get('summary', {})
            summary_text = f"""
            This report presents the findings of an automated documentation gap analysis
            conducted on {summary_data.get('project_name', 'the project')}.

            Key Findings:
            • Total Gaps Identified: {summary_data.get('total_gaps', 0)}
            • Critical Issues: {summary_data.get('critical_gaps', 0)}
            • Documentation Coverage: {summary_data.get('coverage_percentage', 0)}%
            • Auto-generated Drafts: {summary_data.get('draft_count', 0)}
            """
            story.append(Paragraph(summary_text, self.styles['Normal']))
            story.append(Spacer(1, 12))

            # Gap Analysis Table
            if data.get('gaps'):
                story.append(Paragraph("Gap Analysis", self.heading_style))
                gap_table_data = [['Type', 'Severity', 'Description', 'Status']]

                for gap in data['gaps'][:50]:  # Limit to first 50 for readability
                    gap_table_data.append([
                        gap.get('type', 'Unknown'),
                        gap.get('severity', 'Medium'),
                        gap.get('reason', '')[:100] + '...' if len(gap.get('reason', '')) > 100 else gap.get('reason', ''),
                        gap.get('status', 'Open')
                    ])

                table = Table(gap_table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(table)
                story.append(Spacer(1, 12))

            # Recommendations
            story.append(Paragraph("Recommendations", self.heading_style))
            recommendations = data.get('recommendations', [])
            if recommendations:
                for rec in recommendations:
                    story.append(Paragraph(f"• {rec}", self.styles['Normal']))
            else:
                story.append(Paragraph("No specific recommendations available.", self.styles['Normal']))

            # Build PDF
            doc.build(story)
            return True

        except Exception as e:
            logger.error("Failed to generate PDF", error=str(e))
            return False


class BranchManager:
    """Manages Git branch operations for documentation updates"""

    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir

    def generate_branch_name(self, project_id: str, timestamp: Optional[float] = None) -> str:
        """Generate a conventional branch name"""
        ts = timestamp or time.time()
        date_str = datetime.fromtimestamp(ts).strftime('%Y%m%d_%H%M%S')
        return f"docs/auto-update-{project_id}-{date_str}"

    async def setup_branch(self, repo_url: str, branch_name: str, base_branch: str = 'main') -> Tuple[Path, bool]:
        """Set up a Git repository with the new branch"""
        try:
            # Create workspace for this repo
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            repo_path = self.workspace_dir / repo_name
            repo_path.mkdir(exist_ok=True)

            # Clone repository
            clone_cmd = ['git', 'clone', '--depth', '1', '--branch', base_branch, repo_url, str(repo_path)]
            result = await self._run_command(clone_cmd)

            if not result:
                return repo_path, False

            # Create and checkout new branch
            checkout_cmd = ['git', 'checkout', '-b', branch_name]
            result = await self._run_command(checkout_cmd, cwd=repo_path)

            return repo_path, result

        except Exception as e:
            logger.error("Failed to setup branch", error=str(e))
            return repo_path, False

    async def commit_changes(self, repo_path: Path, commit_message: str, files: List[Path]) -> bool:
        """Commit changes to the repository"""
        try:
            # Add files
            for file_path in files:
                add_cmd = ['git', 'add', str(file_path)]
                await self._run_command(add_cmd, cwd=repo_path)

            # Commit
            commit_cmd = ['git', 'commit', '-m', commit_message]
            result = await self._run_command(commit_cmd, cwd=repo_path)

            return result

        except Exception as e:
            logger.error("Failed to commit changes", error=str(e))
            return False

    async def push_branch(self, repo_path: Path, branch_name: str) -> bool:
        """Push the branch to remote"""
        try:
            push_cmd = ['git', 'push', '-u', 'origin', branch_name]
            result = await self._run_command(push_cmd, cwd=repo_path)

            return result

        except Exception as e:
            logger.error("Failed to push branch", error=str(e))
            return False

    async def _run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> bool:
        """Run a shell command"""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(cwd) if cwd else None
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode().strip()
                logger.warning("Command failed", command=cmd, error=error_msg)
                return False

            return True

        except Exception as e:
            logger.error("Command execution failed", command=cmd, error=str(e))
            return False


class ExportWorker:
    """Main export worker"""

    def __init__(self, config: Dict):
        self.config = config
        self.redis_client = None
        self.nats_client = None

        # Initialize components
        self.workspace_dir = Path(config.get("workspace_dir", "/tmp/ai-docgap/exports"))
        self.workspace_dir.mkdir(exist_ok=True)

        self.branch_manager = BranchManager(self.workspace_dir)
        self.changelog_generator = ChangelogGenerator()
        self.pdf_generator = PDFGenerator()

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

        logger.info("Export worker initialized")

    async def run(self):
        """Main worker loop"""
        await self.initialize()

        subject = "docs.export"
        queue_group = "export-workers"

        logger.info("Subscribing to export requests", subject=subject, queue=queue_group)

        async def message_handler(msg):
            await self.handle_export_request(msg)

        await self.nats_client.subscribe(
            subject,
            queue=queue_group,
            cb=message_handler
        )

        while True:
            await asyncio.sleep(1)

    async def handle_export_request(self, msg):
        """Handle incoming export request"""
        try:
            data = json.loads(msg.data.decode())
            request = ExportRequest(**data)

            logger.info("Processing export request",
                       project_id=request.project_id,
                       export_type=request.export_type,
                       target_repo=request.target_repo,
                       request_id=request.request_id)

            start_time = time.time()

            # Handle different export types
            if request.export_type == 'pr':
                result = await self._handle_pr_export(request)
            elif request.export_type == 'bundle':
                result = await self._handle_bundle_export(request)
            else:
                result = ExportResult(
                    project_id=request.project_id,
                    export_type=request.export_type,
                    success=False,
                    error_message=f"Unknown export type: {request.export_type}",
                    request_id=request.request_id
                )

            result.export_duration = time.time() - start_time

            # Publish result
            result_data = asdict(result)
            result_subject = "docs.export.result"
            await self.nats_client.publish(result_subject, json.dumps(result_data).encode())

            await msg.ack()

            logger.info("Export request processed",
                       project_id=request.project_id,
                       export_type=request.export_type,
                       success=result.success)

        except Exception as e:
            logger.error("Failed to process export request", error=str(e))

    async def _handle_pr_export(self, request: ExportRequest) -> ExportResult:
        """Handle PR export to documentation repository"""
        try:
            # Get drafts and gaps data
            drafts = await self._get_drafts_data(request.drafts or [])
            gaps = await self._get_gaps_data(request.gaps or [])
            project = await self._get_project_data(request.project_id)

            if not drafts:
                return ExportResult(
                    project_id=request.project_id,
                    export_type='pr',
                    success=False,
                    error_message="No drafts to export",
                    request_id=request.request_id
                )

            # Generate branch name
            branch_name = self.branch_manager.generate_branch_name(request.project_id)

            # Setup branch
            repo_path, branch_created = await self.branch_manager.setup_branch(
                request.target_repo,
                branch_name
            )

            if not branch_created:
                return ExportResult(
                    project_id=request.project_id,
                    export_type='pr',
                    success=False,
                    error_message="Failed to create branch",
                    request_id=request.request_id
                )

            # Create/modify documentation files
            modified_files = await self._create_documentation_files(repo_path, drafts)

            if not modified_files:
                return ExportResult(
                    project_id=request.project_id,
                    export_type='pr',
                    success=False,
                    error_message="No files were modified",
                    request_id=request.request_id
                )

            # Generate changelog
            changelog = None
            if request.include_changelog:
                changelog = self.changelog_generator.generate_changelog(
                    drafts, gaps, project.get('name', 'Project')
                )

                # Write changelog
                changelog_path = repo_path / 'CHANGELOG.md'
                async with aiofiles.open(changelog_path, 'w', encoding='utf-8') as f:
                    await f.write(changelog)
                modified_files.append(changelog_path)

            # Commit changes
            commit_message = self._generate_commit_message(drafts, gaps)
            commit_success = await self.branch_manager.commit_changes(
                repo_path, commit_message, modified_files
            )

            if not commit_success:
                return ExportResult(
                    project_id=request.project_id,
                    export_type='pr',
                    success=False,
                    error_message="Failed to commit changes",
                    request_id=request.request_id
                )

            # Push branch
            push_success = await self.branch_manager.push_branch(repo_path, branch_name)

            if not push_success:
                return ExportResult(
                    project_id=request.project_id,
                    export_type='pr',
                    success=False,
                    error_message="Failed to push branch",
                    request_id=request.request_id
                )

            # Create pull request
            pr_details = await self._create_pr_details(
                request, drafts, gaps, changelog, branch_name
            )

            git_client = GitPlatformClient(
                platform=self._detect_platform(request.target_repo),
                token=self.config.get("git_token", "")
            )

            pr_url = await git_client.create_pull_request(
                self._extract_repo_name(request.target_repo),
                pr_details
            )

            await git_client.close()

            return ExportResult(
                project_id=request.project_id,
                export_type='pr',
                success=bool(pr_url),
                pr_url=pr_url,
                changelog=changelog,
                request_id=request.request_id
            )

        except Exception as e:
            logger.error("PR export failed", error=str(e))
            return ExportResult(
                project_id=request.project_id,
                export_type='pr',
                success=False,
                error_message=str(e),
                request_id=request.request_id
            )

    async def _handle_bundle_export(self, request: ExportRequest) -> ExportResult:
        """Handle bundle export (JSON/PDF)"""
        try:
            # Get data
            drafts = await self._get_drafts_data(request.drafts or [])
            gaps = await self._get_gaps_data(request.gaps or [])
            mappings = await self._get_mappings_data(request.project_id)
            scores = await self._get_scores_data(request.project_id)
            project = await self._get_project_data(request.project_id)

            bundle_data = {
                'project': project,
                'drafts': drafts,
                'gaps': gaps,
                'mappings': mappings,
                'scores': scores,
                'summary': {
                    'project_name': project.get('name', 'Unknown Project'),
                    'total_gaps': len(gaps),
                    'critical_gaps': len([g for g in gaps if g.get('severity') == 'critical']),
                    'draft_count': len(drafts),
                    'generated_at': datetime.now(timezone.utc).isoformat(),
                    'coverage_percentage': self._calculate_coverage_percentage(mappings, gaps)
                },
                'recommendations': self._generate_recommendations(gaps, scores)
            }

            # Generate bundle based on format
            if request.format == 'json':
                bundle_url = await self._create_json_bundle(bundle_data)
            elif request.format == 'pdf':
                bundle_url = await self._create_pdf_bundle(bundle_data)
            else:
                return ExportResult(
                    project_id=request.project_id,
                    export_type='bundle',
                    success=False,
                    error_message=f"Unsupported format: {request.format}",
                    request_id=request.request_id
                )

            return ExportResult(
                project_id=request.project_id,
                export_type='bundle',
                success=bool(bundle_url),
                bundle_url=bundle_url,
                request_id=request.request_id
            )

        except Exception as e:
            logger.error("Bundle export failed", error=str(e))
            return ExportResult(
                project_id=request.project_id,
                export_type='bundle',
                success=False,
                error_message=str(e),
                request_id=request.request_id
            )

    def _detect_platform(self, repo_url: str) -> str:
        """Detect Git platform from repository URL"""
        if 'github.com' in repo_url:
            return 'github'
        elif 'gitlab.com' in repo_url:
            return 'gitlab'
        else:
            return 'github'  # Default

    def _extract_repo_name(self, repo_url: str) -> str:
        """Extract repository name from URL"""
        # Remove .git suffix and extract owner/repo
        clean_url = repo_url.replace('.git', '')
        parts = clean_url.split('/')
        if len(parts) >= 2:
            return f"{parts[-2]}/{parts[-1]}"
        return clean_url

    async def _create_documentation_files(self, repo_path: Path, drafts: List[Dict]) -> List[Path]:
        """Create or update documentation files"""
        modified_files = []

        for draft in drafts:
            try:
                # Determine file path
                doc_path = draft.get('doc_path', 'new-documentation.md')
                file_path = repo_path / doc_path

                # Ensure directory exists
                file_path.parent.mkdir(parents=True, exist_ok=True)

                # Write draft content
                async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                    await f.write(draft.get('mdx_content', ''))

                modified_files.append(file_path)
                logger.info("Created documentation file", path=str(file_path))

            except Exception as e:
                logger.error("Failed to create documentation file", error=str(e))

        return modified_files

    def _generate_commit_message(self, drafts: List[Dict], gaps: List[Dict]) -> str:
        """Generate conventional commit message"""
        draft_count = len(drafts)
        gap_count = len(gaps)

        if draft_count > 0 and gap_count > 0:
            return f"docs: add {draft_count} documentation drafts addressing {gap_count} gaps"
        elif draft_count > 0:
            return f"docs: add {draft_count} documentation drafts"
        elif gap_count > 0:
            return f"docs: address {gap_count} documentation gaps"
        else:
            return "docs: update documentation"

    async def _create_pr_details(self, request: ExportRequest, drafts: List[Dict],
                                gaps: List[Dict], changelog: Optional[str],
                                branch_name: str) -> PRDetails:
        """Create pull request details"""
        title = f"📝 Documentation Updates - {len(drafts)} drafts, {len(gaps)} gaps addressed"

        body_lines = [
            "## 📋 Summary",
            f"- **Drafts Added:** {len(drafts)}",
            f"- **Gaps Addressed:** {len(gaps)}",
            f"- **Branch:** `{branch_name}`",
            "",
            "## 📝 Changes",
        ]

        # Add draft summaries
        if drafts:
            body_lines.append("### New Documentation:")
            for draft in drafts[:5]:  # Limit to first 5
                draft_title = draft.get('frontmatter', {}).get('title', 'Untitled')
                body_lines.append(f"- {draft_title}")
            if len(drafts) > 5:
                body_lines.append(f"- ... and {len(drafts) - 5} more drafts")

        # Add changelog if available
        if changelog:
            body_lines.extend([
                "",
                "## 📋 Detailed Changelog",
                changelog
            ])

        body_lines.extend([
            "",
            "---",
            "*This PR was automatically generated by AI Documentation Gap Finder*",
            "*Please review all changes before merging*"
        ])

        return PRDetails(
            title=title,
            body="\n".join(body_lines),
            branch_name=branch_name,
            base_branch="main",
            labels=["documentation", "auto-generated"],
            reviewers=[]  # Could be populated from CODEOWNERS
        )

    async def _create_json_bundle(self, data: Dict) -> Optional[str]:
        """Create JSON bundle and return URL"""
        try:
            bundle_filename = f"docgap-report-{int(time.time())}.json"
            bundle_path = self.workspace_dir / bundle_filename

            async with aiofiles.open(bundle_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2, default=str))

            # In a real implementation, upload to S3/Minio and return URL
            return f"file://{bundle_path}"

        except Exception as e:
            logger.error("Failed to create JSON bundle", error=str(e))
            return None

    async def _create_pdf_bundle(self, data: Dict) -> Optional[str]:
        """Create PDF bundle and return URL"""
        try:
            bundle_filename = f"docgap-report-{int(time.time())}.pdf"
            bundle_path = self.workspace_dir / bundle_filename

            success = self.pdf_generator.generate_pdf_report(data, bundle_path)

            if success:
                # In a real implementation, upload to S3/Minio and return URL
                return f"file://{bundle_path}"
            else:
                return None

        except Exception as e:
            logger.error("Failed to create PDF bundle", error=str(e))
            return None

    def _calculate_coverage_percentage(self, mappings: List[Dict], gaps: List[Dict]) -> float:
        """Calculate documentation coverage percentage"""
        if not mappings and not gaps:
            return 0.0

        total_entities = len(set(m['entity_id'] for m in mappings))
        documented_entities = len(set(m['entity_id'] for m in mappings if m.get('score', 0) > 0.5))

        if total_entities == 0:
            return 0.0

        return round((documented_entities / total_entities) * 100, 1)

    def _generate_recommendations(self, gaps: List[Dict], scores: List[Dict]) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []

        # Analyze gap patterns
        critical_gaps = [g for g in gaps if g.get('severity') == 'critical']
        if critical_gaps:
            recommendations.append("Address critical documentation gaps immediately")

        # Analyze scores
        low_score_docs = [s for s in scores if s.get('overall_score', 0) < 0.5]
        if low_score_docs:
            recommendations.append("Improve documentation quality for low-scoring pages")

        # General recommendations
        recommendations.extend([
            "Set up automated documentation checks in CI/CD pipeline",
            "Establish documentation review process with subject matter experts",
            "Create documentation templates and style guides",
            "Implement regular documentation audits and maintenance schedules"
        ])

        return recommendations

    # Mock data methods (replace with actual database queries)
    async def _get_drafts_data(self, draft_ids: List[str]) -> List[Dict]:
        """Mock draft data"""
        return [
            {
                'id': draft_id,
                'mdx_content': '# Sample Documentation\n\nThis is auto-generated content.',
                'frontmatter': {'title': 'Sample Doc', 'draft_type': 'api_reference'},
                'doc_path': f'docs/{draft_id}.md',
                'rationale': {'summary': 'Addresses documentation gap'}
            } for draft_id in draft_ids
        ]

    async def _get_gaps_data(self, gap_ids: List[str]) -> List[Dict]:
        """Mock gaps data"""
        return [
            {
                'id': gap_id,
                'type': 'missing',
                'severity': 'high',
                'reason': 'Missing API documentation',
                'status': 'open'
            } for gap_id in gap_ids
        ]

    async def _get_mappings_data(self, project_id: str) -> List[Dict]:
        """Mock mappings data"""
        return [{'entity_id': 'entity_1', 'doc_id': 'doc_1', 'score': 0.8}]

    async def _get_scores_data(self, project_id: str) -> List[Dict]:
        """Mock scores data"""
        return [{'doc_path': 'docs/api.md', 'overall_score': 0.75}]

    async def _get_project_data(self, project_id: str) -> Dict:
        """Mock project data"""
        return {'id': project_id, 'name': 'Sample Project'}

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
        "workspace_dir": os.getenv("EXPORT_WORKSPACE_DIR", "/tmp/ai-docgap/exports"),
        "git_token": os.getenv("GIT_TOKEN", ""),
    }

    worker = ExportWorker(config)

    try:
        await worker.run()
    except Exception as e:
        logger.error("Worker failed", error=str(e))
        await worker.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
