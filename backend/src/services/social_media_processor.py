"""
Social media processor - handles TikTok and Instagram posts (no HTML extraction)
"""
import logging
from typing import Dict, List, Tuple

from services.base_processor import BaseContentProcessor
from ai_client import AIClient

logger = logging.getLogger(__name__)


class SocialMediaProcessor(BaseContentProcessor):
    """
    Processor for social media content (TikTok, Instagram).

    Features:
    - Works with video/post metadata (captions, descriptions)
    - AI text analysis on captions
    - Extracts hashtags and mentions
    - No HTML/article extraction (not applicable)
    """

    def __init__(
        self,
        ai_client: AIClient,
        brands: List[str] = None,
        config: Dict = None
    ):
        """
        Initialize social media processor

        Args:
            ai_client: AIClient instance for content analysis
            brands: List of known brands to track
            config: Configuration options (future use)
        """
        super().__init__(ai_client, brands, config)

    def process_item(self, item: Dict) -> Tuple[Dict, str]:
        """
        Process a social media post item

        Args:
            item: Social media item dict with keys:
                - title: str (caption/description)
                - link: str (post URL)
                - raw_summary: str (additional text)
                - source: str (e.g., "TikTok (@username)")
                - provider: str (TIKTOK or INSTAGRAM)
                - metadata: Dict (hashtags, mentions, views, likes, etc.)

        Returns:
            Tuple of (processed_data dict, dedupe_key str)
        """
        title = item.get('title', '')
        link = item.get('link', '')
        raw_summary = item.get('raw_summary', '')
        provider = item.get('provider', 'SOCIAL_MEDIA')
        source = item.get('source', provider)
        metadata = item.get('metadata', {})

        logger.info(f"Processing social media post: {title[:100]}")

        # Step 1: Combine title and summary as "full text"
        # (Social media posts don't have separate article content)
        full_text = f"{title}\n\n{raw_summary}".strip()
        if not full_text:
            full_text = title or raw_summary or "No content"

        logger.info(f"Social media content length: {len(full_text)} chars")

        # Step 2: AI text analysis on caption/description
        logger.info(f"Analyzing social media caption")
        analysis = self.ai_client.classify_summarize(full_text, self.brands)

        # Step 3: Extract brands from text analysis
        mentioned_brands = analysis.get('brands', [])
        logger.info(f"Text analysis extracted brands: {mentioned_brands}")

        # Step 4: Extract hashtags from metadata (if available)
        hashtags = metadata.get('hashtags', [])
        if hashtags:
            logger.info(f"Found {len(hashtags)} hashtags: {hashtags}")

        # Step 5: Generate dedupe key
        dedupe_key = self.generate_dedupe_key(title, link)

        # Step 6: Return processed data
        processed_data = {
            'full_text': full_text[:5000],  # Limit size for database
            'brands': mentioned_brands,
            'summary': analysis.get('short_summary', ''),
            'sentiment': analysis.get('sentiment', 'neutral'),
            'topic': analysis.get('topic', 'general'),
            'est_reach': metadata.get('views', metadata.get('likes', analysis.get('est_reach', 0))),
            'provider': provider,
            'source': source,
            'title': title,
            'link': link,
            'metadata': {
                'hashtags': hashtags,
                'mentions': metadata.get('mentions', []),
                'likes': metadata.get('likes', 0),
                'views': metadata.get('views', 0),
                'comments': metadata.get('comments', 0),
                'shares': metadata.get('shares', 0),
            }
        }

        return processed_data, dedupe_key

    def get_supported_providers(self) -> List[str]:
        """Return list of providers this processor supports"""
        return ['TIKTOK', 'INSTAGRAM']
