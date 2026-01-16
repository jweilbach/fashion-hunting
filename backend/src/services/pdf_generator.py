"""
PDF Generator Service - Creates PDF summary documents

Uses reportlab to generate professional PDF documents summarizing
brand mentions and media coverage.
"""
import io
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

logger = logging.getLogger(__name__)


class PDFGenerator:
    """
    Generates PDF summary documents for brand media coverage.

    Creates professional multi-page PDFs with:
    - Title and date range
    - Executive summary
    - Sentiment breakdown
    - Platform activity
    - Top mentions
    """

    def __init__(self):
        """Initialize PDF generator with default styles."""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles for the PDF."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#1a1a2e'),
            alignment=TA_CENTER
        ))

        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#4a4a6a'),
            alignment=TA_CENTER,
            spaceAfter=20
        ))

        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.HexColor('#2d2d44'),
            borderColor=colors.HexColor('#e0e0e0'),
            borderWidth=1,
            borderPadding=5
        ))

        # Body text style
        self.styles.add(ParagraphStyle(
            name='BodyText',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceAfter=12
        ))

        # Highlight style for important text
        self.styles.add(ParagraphStyle(
            name='Highlight',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#2563eb'),
            spaceBefore=6,
            spaceAfter=6
        ))

    def generate_summary_pdf(
        self,
        title: str,
        executive_summary: str,
        period_start: datetime,
        period_end: datetime,
        brands: List[str],
        reports: List[Dict[str, Any]],
        sentiment_stats: Dict[str, int],
        provider_stats: Dict[str, Dict[str, int]],
        top_brands: List[tuple]
    ) -> bytes:
        """
        Generate a complete summary PDF document.

        Args:
            title: Summary document title
            executive_summary: AI-generated executive summary text
            period_start: Start of the reporting period
            period_end: End of the reporting period
            brands: List of brand names covered
            reports: List of report dictionaries
            sentiment_stats: Dict of sentiment -> count
            provider_stats: Dict of provider -> {count, reach}
            top_brands: List of (brand_name, mention_count) tuples

        Returns:
            PDF file content as bytes
        """
        buffer = io.BytesIO()

        # Create the PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )

        # Build the document content
        story = []

        # Title page
        story.extend(self._build_title_page(
            title, period_start, period_end, brands, len(reports)
        ))

        # Executive summary section
        story.extend(self._build_executive_summary(executive_summary))

        # Key metrics section
        story.extend(self._build_key_metrics(
            sentiment_stats, provider_stats, len(reports)
        ))

        # Sentiment breakdown
        story.extend(self._build_sentiment_section(sentiment_stats))

        # Platform activity
        story.extend(self._build_platform_section(provider_stats))

        # Top mentions
        if top_brands:
            story.extend(self._build_top_brands_section(top_brands))

        # Recent highlights (top 10 reports)
        if reports:
            story.extend(self._build_highlights_section(reports[:10]))

        # Build the PDF
        try:
            doc.build(story)
            pdf_bytes = buffer.getvalue()
            logger.info(f"Generated PDF: {len(pdf_bytes)} bytes")
            return pdf_bytes
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            raise
        finally:
            buffer.close()

    def _build_title_page(
        self,
        title: str,
        period_start: datetime,
        period_end: datetime,
        brands: List[str],
        report_count: int
    ) -> List:
        """Build the title page elements."""
        elements = []

        # Add some space at the top
        elements.append(Spacer(1, 1.5*inch))

        # Title
        elements.append(Paragraph(title, self.styles['CustomTitle']))

        # Date range
        date_range = f"{period_start.strftime('%B %d, %Y')} - {period_end.strftime('%B %d, %Y')}"
        elements.append(Paragraph(date_range, self.styles['Subtitle']))

        # Report count
        elements.append(Paragraph(
            f"<b>{report_count}</b> media mentions analyzed",
            self.styles['Subtitle']
        ))

        # Brands covered
        if brands:
            brand_text = f"Brands: {', '.join(brands[:5])}"
            if len(brands) > 5:
                brand_text += f" and {len(brands) - 5} more"
            elements.append(Spacer(1, 0.5*inch))
            elements.append(Paragraph(brand_text, self.styles['Subtitle']))

        # Generated timestamp
        elements.append(Spacer(1, 1*inch))
        generated_text = f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
        elements.append(Paragraph(generated_text, self.styles['Normal']))

        # Page break after title page
        elements.append(PageBreak())

        return elements

    def _build_executive_summary(self, summary_text: str) -> List:
        """Build the executive summary section."""
        elements = []

        elements.append(Paragraph("Executive Summary", self.styles['SectionHeader']))

        # Split summary into paragraphs if it contains newlines
        paragraphs = summary_text.split('\n\n') if summary_text else ['No summary available.']
        for para in paragraphs:
            if para.strip():
                elements.append(Paragraph(para.strip(), self.styles['BodyText']))

        elements.append(Spacer(1, 0.25*inch))

        return elements

    def _build_key_metrics(
        self,
        sentiment_stats: Dict[str, int],
        provider_stats: Dict[str, Dict[str, int]],
        report_count: int
    ) -> List:
        """Build the key metrics summary section."""
        elements = []

        elements.append(Paragraph("Key Metrics", self.styles['SectionHeader']))

        # Calculate totals
        total_reach = sum(
            stats.get('total_reach', 0)
            for stats in provider_stats.values()
        )
        total_positive = sentiment_stats.get('positive', 0)
        total_negative = sentiment_stats.get('negative', 0)
        total_sentiment = sum(sentiment_stats.values()) or 1
        positive_rate = (total_positive / total_sentiment) * 100

        # Create metrics table
        metrics_data = [
            ['Total Mentions', 'Total Reach', 'Positive Sentiment', 'Platforms'],
            [
                str(report_count),
                f"{total_reach:,}",
                f"{positive_rate:.0f}%",
                str(len(provider_stats))
            ]
        ]

        metrics_table = Table(
            metrics_data,
            colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch]
        )
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f4f8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#4a4a6a')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, 1), 14),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#2563eb')),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 1), (-1, 1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
        ]))

        elements.append(metrics_table)
        elements.append(Spacer(1, 0.25*inch))

        return elements

    def _build_sentiment_section(self, sentiment_stats: Dict[str, int]) -> List:
        """Build the sentiment breakdown section."""
        elements = []

        elements.append(Paragraph("Sentiment Analysis", self.styles['SectionHeader']))

        total = sum(sentiment_stats.values()) or 1

        # Create sentiment table
        table_data = [['Sentiment', 'Count', 'Percentage']]

        sentiment_colors = {
            'positive': colors.HexColor('#22c55e'),
            'neutral': colors.HexColor('#6b7280'),
            'negative': colors.HexColor('#ef4444'),
        }

        for sentiment in ['positive', 'neutral', 'negative']:
            count = sentiment_stats.get(sentiment, 0)
            percentage = (count / total) * 100
            table_data.append([
                sentiment.title(),
                str(count),
                f"{percentage:.1f}%"
            ])

        sentiment_table = Table(
            table_data,
            colWidths=[2*inch, 1.5*inch, 1.5*inch]
        )
        sentiment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f4f8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#4a4a6a')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
            # Color code the sentiment rows
            ('TEXTCOLOR', (0, 1), (0, 1), sentiment_colors['positive']),
            ('TEXTCOLOR', (0, 2), (0, 2), sentiment_colors['neutral']),
            ('TEXTCOLOR', (0, 3), (0, 3), sentiment_colors['negative']),
        ]))

        elements.append(sentiment_table)
        elements.append(Spacer(1, 0.25*inch))

        return elements

    def _build_platform_section(self, provider_stats: Dict[str, Dict[str, int]]) -> List:
        """Build the platform activity section."""
        elements = []

        elements.append(Paragraph("Activity by Platform", self.styles['SectionHeader']))

        if not provider_stats:
            elements.append(Paragraph("No platform data available.", self.styles['BodyText']))
            return elements

        # Create platform table
        table_data = [['Platform', 'Mentions', 'Total Reach']]

        # Sort by mention count
        sorted_providers = sorted(
            provider_stats.items(),
            key=lambda x: x[1].get('report_count', 0),
            reverse=True
        )

        for provider, stats in sorted_providers:
            count = stats.get('report_count', 0)
            reach = stats.get('total_reach', 0)
            table_data.append([
                provider.title(),
                str(count),
                f"{reach:,}"
            ])

        platform_table = Table(
            table_data,
            colWidths=[2.5*inch, 1.5*inch, 2*inch]
        )
        platform_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f4f8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#4a4a6a')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
        ]))

        elements.append(platform_table)
        elements.append(Spacer(1, 0.25*inch))

        return elements

    def _build_top_brands_section(self, top_brands: List[tuple]) -> List:
        """Build the top mentioned brands section."""
        elements = []

        elements.append(Paragraph("Top Mentioned Brands", self.styles['SectionHeader']))

        # Create brands table
        table_data = [['Rank', 'Brand', 'Mentions']]

        for idx, (brand, count) in enumerate(top_brands[:10], 1):
            table_data.append([str(idx), brand, str(count)])

        brands_table = Table(
            table_data,
            colWidths=[0.75*inch, 3.5*inch, 1.5*inch]
        )
        brands_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f4f8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#4a4a6a')),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
        ]))

        elements.append(brands_table)
        elements.append(Spacer(1, 0.25*inch))

        return elements

    def _build_highlights_section(self, reports: List[Dict[str, Any]]) -> List:
        """Build the recent highlights section."""
        elements = []

        elements.append(PageBreak())
        elements.append(Paragraph("Recent Highlights", self.styles['SectionHeader']))

        for idx, report in enumerate(reports, 1):
            # Title with sentiment indicator
            sentiment = report.get('sentiment', 'neutral')
            sentiment_indicator = {
                'positive': '(+)',
                'neutral': '(=)',
                'negative': '(-)'
            }.get(sentiment, '')

            title = report.get('title', 'Untitled')
            if len(title) > 100:
                title = title[:97] + '...'

            elements.append(Paragraph(
                f"<b>{idx}. {title}</b> {sentiment_indicator}",
                self.styles['Normal']
            ))

            # Source and date
            source = report.get('source', report.get('provider', 'Unknown'))
            timestamp = report.get('timestamp', '')
            if timestamp and isinstance(timestamp, str):
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    timestamp = dt.strftime('%b %d, %Y')
                except Exception:
                    pass

            elements.append(Paragraph(
                f"<i>{source} | {timestamp}</i>",
                self.styles['Normal']
            ))

            # Summary
            summary = report.get('summary', '')
            if summary:
                if len(summary) > 200:
                    summary = summary[:197] + '...'
                elements.append(Paragraph(summary, self.styles['BodyText']))

            elements.append(Spacer(1, 0.15*inch))

        return elements
