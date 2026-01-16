"""
Summary Service - Orchestrates AI summary generation

Coordinates between:
- Report repository (fetching reports)
- AI client (generating executive summaries via Gemini or OpenAI)
- PDF generator (creating PDF documents)
- File storage (saving PDFs - local or S3)
"""
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import desc

from models.summary import Summary
from models.report import Report
from models.brand import BrandConfig
from repositories.report_repository import ReportRepository
from services.file_storage_service import FileStorageService
from services.pdf_generator import PDFGenerator

logger = logging.getLogger(__name__)

# AI Provider constants
AI_PROVIDER_GEMINI = 'gemini'
AI_PROVIDER_OPENAI = 'openai'


class SummaryService:
    """
    Service for generating AI-powered summary documents.

    Orchestrates the entire summary generation process:
    1. Fetch reports from the time period
    2. Aggregate statistics
    3. Generate AI executive summary
    4. Create PDF document
    5. Store PDF and update summary record
    """

    def __init__(
        self,
        db: Session,
        report_repo: Optional[ReportRepository] = None,
        file_storage: Optional[FileStorageService] = None,
        pdf_generator: Optional[PDFGenerator] = None
    ):
        """
        Initialize summary service.

        Args:
            db: SQLAlchemy database session
            report_repo: Optional custom report repository
            file_storage: Optional custom file storage service
            pdf_generator: Optional custom PDF generator
        """
        self.db = db
        self.report_repo = report_repo or ReportRepository(db)
        self.file_storage = file_storage or FileStorageService()
        self.pdf_generator = pdf_generator or PDFGenerator()

        # AI configuration - prefer Gemini, fallback to OpenAI
        self._gemini_api_key = os.getenv('GEMINI_API_KEY')
        self._openai_api_key = os.getenv('OPENAI_API_KEY')

        # Determine which AI provider to use
        if self._gemini_api_key:
            self._ai_provider = AI_PROVIDER_GEMINI
            logger.info("SummaryService using Gemini for AI summaries")
        elif self._openai_api_key:
            self._ai_provider = AI_PROVIDER_OPENAI
            logger.info("SummaryService using OpenAI for AI summaries")
        else:
            self._ai_provider = None
            logger.warning("No AI API key configured - summaries will use template fallback")

    def create_summary_record(
        self,
        tenant_id: UUID,
        title: str,
        brand_ids: List[UUID],
        job_id: Optional[UUID] = None,
        execution_id: Optional[UUID] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> Summary:
        """
        Create a new summary record with pending status.

        Args:
            tenant_id: Tenant UUID
            title: Summary document title
            brand_ids: List of brand UUIDs to include
            job_id: Optional associated job ID
            execution_id: Optional associated execution ID
            period_start: Start of reporting period
            period_end: End of reporting period

        Returns:
            Created Summary object
        """
        summary = Summary(
            tenant_id=tenant_id,
            title=title,
            brand_ids=brand_ids,
            job_id=job_id,
            execution_id=execution_id,
            period_start=period_start or (datetime.now(timezone.utc) - timedelta(days=7)),
            period_end=period_end or datetime.now(timezone.utc),
            generation_status='pending'
        )

        self.db.add(summary)
        self.db.commit()
        self.db.refresh(summary)

        logger.info(f"Created summary record {summary.id} for tenant {tenant_id}")
        return summary

    def generate_summary_for_execution(
        self,
        tenant_id: UUID,
        job_id: UUID,
        execution_id: UUID,
        brand_ids: List[UUID],
        title: Optional[str] = None
    ) -> Summary:
        """
        Generate a summary for a completed job execution.

        This is the main entry point called after job execution completes.

        Args:
            tenant_id: Tenant UUID
            job_id: Job UUID
            execution_id: Execution UUID
            brand_ids: List of brand UUIDs included in the job
            title: Optional custom title

        Returns:
            Updated Summary object with generated PDF
        """
        # Default title
        if not title:
            title = f"Media Coverage Summary - {datetime.now().strftime('%B %d, %Y')}"

        # Create summary record
        summary = self.create_summary_record(
            tenant_id=tenant_id,
            title=title,
            brand_ids=brand_ids,
            job_id=job_id,
            execution_id=execution_id
        )

        # Generate the summary
        return self.generate_summary(summary.id)

    def generate_summary(self, summary_id: UUID) -> Summary:
        """
        Generate a complete summary document for an existing summary record.

        Args:
            summary_id: Summary UUID

        Returns:
            Updated Summary object with generated PDF
        """
        # Load summary
        summary = self.db.query(Summary).filter(Summary.id == summary_id).first()
        if not summary:
            raise ValueError(f"Summary {summary_id} not found")

        # Update status to generating
        summary.generation_status = 'generating'
        self.db.commit()

        try:
            # Fetch reports for the time period
            reports = self._fetch_reports(
                tenant_id=summary.tenant_id,
                brand_ids=summary.brand_ids,
                period_start=summary.period_start,
                period_end=summary.period_end
            )

            if not reports:
                raise ValueError("No reports found for the specified period")

            # Get brand names
            brand_names = self._get_brand_names(summary.tenant_id, summary.brand_ids)

            # Aggregate statistics
            sentiment_stats = self._aggregate_sentiment(reports)
            provider_stats = self._aggregate_providers(reports)
            top_brands = self._get_top_brands(reports)

            # Generate AI executive summary
            executive_summary = self._generate_executive_summary(
                reports=reports,
                brand_names=brand_names,
                sentiment_stats=sentiment_stats,
                provider_stats=provider_stats
            )

            # Generate PDF
            pdf_bytes = self.pdf_generator.generate_summary_pdf(
                title=summary.title,
                executive_summary=executive_summary,
                period_start=summary.period_start,
                period_end=summary.period_end,
                brands=brand_names,
                reports=[r.to_dict() for r in reports],
                sentiment_stats=sentiment_stats,
                provider_stats=provider_stats,
                top_brands=top_brands
            )

            # Save PDF to storage with title and date for readable filename
            file_path = self.file_storage.save_pdf(
                tenant_id=summary.tenant_id,
                summary_id=summary.id,
                pdf_bytes=pdf_bytes,
                title=summary.title,
                created_at=summary.created_at
            )

            # Update summary record
            summary.executive_summary = executive_summary
            summary.file_path = file_path
            summary.file_size_bytes = len(pdf_bytes)
            summary.report_count = len(reports)
            summary.generation_status = 'completed'
            summary.generation_error = None

            self.db.commit()
            self.db.refresh(summary)

            logger.info(f"Generated summary {summary.id}: {len(reports)} reports, {len(pdf_bytes)} bytes")
            return summary

        except Exception as e:
            logger.error(f"Failed to generate summary {summary_id}: {e}", exc_info=True)

            # Update status to failed
            summary.generation_status = 'failed'
            summary.generation_error = str(e)
            self.db.commit()

            raise

    def _fetch_reports(
        self,
        tenant_id: UUID,
        brand_ids: List[UUID],
        period_start: datetime,
        period_end: datetime
    ) -> List[Report]:
        """Fetch reports for the summary period."""
        query = self.db.query(Report).filter(
            Report.tenant_id == tenant_id,
            Report.processing_status == 'completed',
            Report.timestamp >= period_start,
            Report.timestamp <= period_end
        )

        # Note: If brand_ids filtering is needed, we'd need to match against
        # the brand names in the report's brands array. For now, we get all
        # reports for the tenant in the time period.

        reports = query.order_by(desc(Report.timestamp)).limit(500).all()
        logger.info(f"Fetched {len(reports)} reports for summary")
        return reports

    def _get_brand_names(self, tenant_id: UUID, brand_ids: List[UUID]) -> List[str]:
        """Get brand names from brand IDs."""
        if not brand_ids:
            return []

        brands = self.db.query(BrandConfig).filter(
            BrandConfig.tenant_id == tenant_id,
            BrandConfig.id.in_(brand_ids)
        ).all()

        return [b.brand_name for b in brands]

    def _aggregate_sentiment(self, reports: List[Report]) -> Dict[str, int]:
        """Aggregate sentiment counts from reports."""
        stats = {'positive': 0, 'neutral': 0, 'negative': 0}
        for report in reports:
            sentiment = report.sentiment or 'neutral'
            if sentiment in stats:
                stats[sentiment] += 1
            else:
                stats['neutral'] += 1
        return stats

    def _aggregate_providers(self, reports: List[Report]) -> Dict[str, Dict[str, int]]:
        """Aggregate provider statistics from reports."""
        stats = {}
        for report in reports:
            provider = report.provider or 'Unknown'
            if provider not in stats:
                stats[provider] = {'report_count': 0, 'total_reach': 0}
            stats[provider]['report_count'] += 1
            stats[provider]['total_reach'] += report.est_reach or 0
        return stats

    def _get_top_brands(self, reports: List[Report], limit: int = 10) -> List[Tuple[str, int]]:
        """Get top mentioned brands from reports."""
        brand_counts = {}
        for report in reports:
            for brand in (report.brands or []):
                brand_counts[brand] = brand_counts.get(brand, 0) + 1

        sorted_brands = sorted(
            brand_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_brands[:limit]

    def _generate_executive_summary(
        self,
        reports: List[Report],
        brand_names: List[str],
        sentiment_stats: Dict[str, int],
        provider_stats: Dict[str, Dict[str, int]]
    ) -> str:
        """
        Generate AI executive summary using Gemini (preferred) or OpenAI.

        Falls back to a template-based summary if AI is unavailable.
        """
        # Calculate key metrics for the prompt
        total_reports = len(reports)
        total_reach = sum(s.get('total_reach', 0) for s in provider_stats.values())
        total_positive = sentiment_stats.get('positive', 0)
        total_negative = sentiment_stats.get('negative', 0)
        total_sentiment = sum(sentiment_stats.values()) or 1
        positive_rate = (total_positive / total_sentiment) * 100

        # Get top platforms
        top_platforms = sorted(
            provider_stats.items(),
            key=lambda x: x[1].get('report_count', 0),
            reverse=True
        )[:3]

        # Get sample report titles for context
        sample_titles = [r.title for r in reports[:10] if r.title]

        # Build the prompt
        prompt = f"""You are a PR analyst creating an executive summary for a media coverage report.

Key Metrics:
- Total mentions: {total_reports}
- Estimated total reach: {total_reach:,}
- Sentiment: {positive_rate:.0f}% positive, {total_negative} negative
- Top platforms: {', '.join(p[0] for p in top_platforms)}
- Brands tracked: {', '.join(brand_names[:5]) if brand_names else 'Various brands'}

Sample headlines from the coverage:
{chr(10).join(f'- {t}' for t in sample_titles[:5])}

Write a 2-3 paragraph executive summary that:
1. Highlights the overall media presence and reach
2. Notes sentiment trends and any concerns
3. Mentions key platforms and content types
4. Provides actionable insights for the brand team

Keep it professional and concise. Do not use bullet points or headers."""

        # Try AI generation based on configured provider
        if self._ai_provider == AI_PROVIDER_GEMINI:
            try:
                content = self._call_gemini_api(prompt)
                logger.info("Generated AI executive summary using Gemini")
                return content
            except Exception as e:
                logger.warning(f"Gemini summary generation failed: {e}")
                # Try OpenAI fallback if available
                if self._openai_api_key:
                    try:
                        content = self._call_openai_api(prompt)
                        logger.info("Generated AI executive summary using OpenAI (fallback)")
                        return content
                    except Exception as e2:
                        logger.warning(f"OpenAI fallback also failed: {e2}")

        elif self._ai_provider == AI_PROVIDER_OPENAI:
            try:
                content = self._call_openai_api(prompt)
                logger.info("Generated AI executive summary using OpenAI")
                return content
            except Exception as e:
                logger.warning(f"OpenAI summary generation failed: {e}")

        # Fallback to template-based summary
        logger.info("Using template-based summary (no AI available)")
        return self._generate_template_summary(
            total_reports=total_reports,
            total_reach=total_reach,
            positive_rate=positive_rate,
            sentiment_stats=sentiment_stats,
            top_platforms=top_platforms,
            brand_names=brand_names
        )

    def _call_gemini_api(self, prompt: str) -> str:
        """
        Call Google Gemini API to generate text.

        Args:
            prompt: The prompt to send to Gemini

        Returns:
            Generated text content
        """
        import requests

        # Use Gemini 1.5 Flash for fast, cost-effective generation
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self._gemini_api_key}"

        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 1000,
                    "topP": 0.95,
                    "topK": 40
                },
                "safetySettings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                ]
            },
            timeout=60
        )
        response.raise_for_status()

        result = response.json()
        content = result["candidates"][0]["content"]["parts"][0]["text"]
        return content.strip()

    def _call_openai_api(self, prompt: str) -> str:
        """
        Call OpenAI API to generate text.

        Args:
            prompt: The prompt to send to OpenAI

        Returns:
            Generated text content
        """
        import requests

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self._openai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 500
            },
            timeout=60
        )
        response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        return content.strip()

    def _generate_template_summary(
        self,
        total_reports: int,
        total_reach: int,
        positive_rate: float,
        sentiment_stats: Dict[str, int],
        top_platforms: List[Tuple[str, Dict[str, int]]],
        brand_names: List[str]
    ) -> str:
        """Generate a template-based summary when AI is unavailable."""
        brands_text = ', '.join(brand_names[:3]) if brand_names else "the tracked brands"

        platform_names = [p[0] for p in top_platforms]
        platforms_text = ', '.join(platform_names) if platform_names else "various platforms"

        sentiment_desc = "predominantly positive" if positive_rate >= 60 else (
            "mixed" if positive_rate >= 40 else "challenging"
        )

        return f"""During this reporting period, {brands_text} received {total_reports:,} media mentions across {platforms_text}, generating an estimated reach of {total_reach:,} impressions.

The overall sentiment was {sentiment_desc}, with {sentiment_stats.get('positive', 0)} positive mentions, {sentiment_stats.get('neutral', 0)} neutral, and {sentiment_stats.get('negative', 0)} negative. This indicates {'strong brand favorability' if positive_rate >= 60 else 'opportunities for improved messaging'} in the current media landscape.

The most active coverage came from {platform_names[0] if platform_names else 'social media'}, suggesting this channel continues to drive the majority of brand conversation. Consider focusing engagement efforts on these high-performing platforms while monitoring sentiment trends for emerging narratives."""

    def get_summary(self, summary_id: UUID) -> Optional[Summary]:
        """Get a summary by ID."""
        return self.db.query(Summary).filter(Summary.id == summary_id).first()

    def get_summaries(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[str] = None
    ) -> Tuple[List[Summary], int]:
        """
        Get paginated list of summaries for a tenant.

        Args:
            tenant_id: Tenant UUID
            page: Page number (1-indexed)
            page_size: Items per page
            status_filter: Optional status to filter by

        Returns:
            Tuple of (summaries list, total count)
        """
        query = self.db.query(Summary).filter(Summary.tenant_id == tenant_id)

        if status_filter:
            query = query.filter(Summary.generation_status == status_filter)

        total = query.count()

        summaries = (
            query
            .order_by(desc(Summary.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return summaries, total

    def get_recent_summaries(self, tenant_id: UUID, limit: int = 3) -> List[Summary]:
        """Get recent completed summaries for dashboard display."""
        return (
            self.db.query(Summary)
            .filter(
                Summary.tenant_id == tenant_id,
                Summary.generation_status == 'completed'
            )
            .order_by(desc(Summary.created_at))
            .limit(limit)
            .all()
        )

    def delete_summary(self, summary_id: UUID) -> bool:
        """
        Delete a summary and its associated PDF file.

        Args:
            summary_id: Summary UUID

        Returns:
            True if deleted, False if not found
        """
        summary = self.db.query(Summary).filter(Summary.id == summary_id).first()
        if not summary:
            return False

        # Delete the PDF file if it exists
        if summary.file_path:
            try:
                self.file_storage.delete_file(summary.file_path)
            except Exception as e:
                logger.warning(f"Failed to delete PDF file: {e}")

        # Delete the database record
        self.db.delete(summary)
        self.db.commit()

        logger.info(f"Deleted summary {summary_id}")
        return True
