"""
Article processor - handles RSS and Google Search articles with full HTML extraction
"""
import logging
from typing import Dict, List, Tuple

from services.base_processor import BaseContentProcessor
from fetch_and_report_db import fetch_full_article_text
from ai_client import AIClient

logger = logging.getLogger(__name__)


class ArticleProcessor(BaseContentProcessor):
    """
    Processor for web articles (RSS, Google Search results).

    Features:
    - Fetches full article HTML and text
    - Extracts article content using Trafilatura
    - AI text analysis
    - HTML brand extraction (optional)
    """

    def __init__(
        self,
        ai_client: AIClient,
        brands: List[str] = None,
        config: Dict = None
    ):
        """
        Initialize article processor

        Args:
            ai_client: AIClient instance for content analysis
            brands: List of known brands to track
            config: Configuration options:
                - enable_html_brand_extraction: bool (default True)
                - ignore_brand_exact: List[str] (brands to ignore)
                - ignore_brand_patterns: List[str] (regex patterns to ignore)
                - max_html_size_bytes: int|None (max HTML size to process, None = unlimited, default 500000)
                - extra_meta_names: List[str] (extra meta tags to extract)
                - extra_meta_properties: List[str]
                - extra_itemprops: List[str]
        """
        super().__init__(ai_client, brands, config)

        self.enable_html_brand_extraction = config.get('enable_html_brand_extraction', True)
        self.ignore_brand_exact = config.get('ignore_brand_exact', [])
        self.ignore_brand_patterns = config.get('ignore_brand_patterns', [])
        self.max_html_size_bytes = config.get('max_html_size_bytes', 500000)
        self.extra_meta_names = config.get('extra_meta_names', [])
        self.extra_meta_properties = config.get('extra_meta_properties', [])
        self.extra_itemprops = config.get('extra_itemprops', [])

    def process_item(self, item: Dict) -> Tuple[Dict, str]:
        """
        Process a web article item

        Args:
            item: Article item dict with keys:
                - title: str
                - link: str
                - raw_summary: str
                - source: str
                - provider: str

        Returns:
            Tuple of (processed_data dict, dedupe_key str)
        """
        title = item.get('title', '')
        link = item.get('link', '')
        raw_summary = item.get('raw_summary', '')
        provider = item.get('provider', 'RSS')
        source = item.get('source', provider)

        logger.info(f"Processing article: {title}")

        # Step 1: Fetch full article text and HTML (only fetch HTML if needed)
        logger.info(f"Fetching full article from: {link}")
        full_text, html_bytes = fetch_full_article_text(
            link,
            title,
            raw_summary,
            extra_meta_names=self.extra_meta_names,
            extra_meta_properties=self.extra_meta_properties,
            extra_itemprops=self.extra_itemprops,
            return_html=self.enable_html_brand_extraction
        )

        # Fallback to title + summary if fetch failed
        if len(full_text) < 100:
            logger.warning(f"Full article fetch failed, using title + summary")
            full_text = f"{title}\n\n{raw_summary}"
            html_bytes = None

        # Step 2: AI text analysis
        logger.info(f"Analyzing article text ({len(full_text)} chars)")
        analysis = self.ai_client.classify_summarize(full_text, self.brands)

        # Step 3: Extract brands from text
        mentioned_brands = analysis.get('brands', [])
        logger.info(f"Text analysis extracted brands: {mentioned_brands}")

        # Step 4: Extract brands from HTML (if enabled and available)
        if self.enable_html_brand_extraction and html_bytes:
            logger.info(f"Extracting brands from HTML ({len(html_bytes)} bytes)")
            try:
                brands_from_html = self.ai_client.ai_extract_brands_from_raw_html(
                    html_bytes,
                    ignore_exact=self.ignore_brand_exact,
                    ignore_patterns=self.ignore_brand_patterns,
                    max_html_size=self.max_html_size_bytes
                )
                logger.info(f"HTML analysis extracted brands: {brands_from_html}")

                # Merge brands from both sources (avoid duplicates)
                seen = set(b.lower() for b in mentioned_brands)
                for b in brands_from_html:
                    if b.lower() not in seen:
                        mentioned_brands.append(b)
                        seen.add(b.lower())

                logger.info(f"Combined brands after HTML merge: {mentioned_brands}")
            except Exception as html_error:
                logger.warning(f"HTML brand extraction failed: {html_error}")

        # Step 5: Generate dedupe key
        dedupe_key = self.generate_dedupe_key(title, link)

        # Step 6: Return processed data
        processed_data = {
            'full_text': full_text[:5000],  # Limit size for database
            'brands': mentioned_brands,
            'summary': analysis.get('short_summary', ''),
            'sentiment': analysis.get('sentiment', 'neutral'),
            'topic': analysis.get('topic', 'general'),
            'est_reach': analysis.get('est_reach', 0),
            'provider': provider,
            'source': source,
            'title': title,
            'link': link,
            'metadata': {
                'html_extracted': html_bytes is not None,
                'full_text_length': len(full_text)
            }
        }

        return processed_data, dedupe_key

    def get_supported_providers(self) -> List[str]:
        """Return list of providers this processor supports"""
        return ['RSS', 'GOOGLE_SEARCH']
