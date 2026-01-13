"""
Instagram Processor - processor for Instagram posts with AI brand extraction
Combines hashtag/mention matching with AI-powered brand detection from captions
"""
import logging
from typing import Dict, List, Tuple

from services.base_processor import BaseContentProcessor
from utils.brand_matcher import BrandMatcher
from ai_client import AIClient

logger = logging.getLogger(__name__)


class InstagramProcessor(BaseContentProcessor):
    """
    Processor for Instagram posts with AI brand extraction

    Focuses on:
    - AI brand extraction from captions (finds ALL brands)
    - Hashtag/mention brand matching (for tracked brands)
    - Engagement metrics (likes, comments, views)
    - Influencer identification
    - EMV calculation

    Skips:
    - AI sentiment analysis (visual content, not text-heavy)
    - AI summarization (captions are already short)
    - Topic classification (already filtered by hashtag)
    """

    def __init__(self, ai_client: AIClient, brands: List[str] = None, config: Dict = None):
        """
        Initialize Instagram processor

        Args:
            ai_client: AIClient instance for brand extraction from captions
            brands: List of brand names to track (used for hashtag matching)
            config: Configuration options:
                - enable_ai_brand_extraction: bool (default True) - Use AI to extract ALL brands from captions
        """
        super().__init__(ai_client=ai_client, brands=brands, config=config)

        # Configuration option to enable/disable AI brand extraction
        self.enable_ai_brand_extraction = config.get('enable_ai_brand_extraction', True) if config else True

    def process_item(self, item: Dict) -> Tuple[Dict, str]:
        """
        Process an Instagram post item

        Args:
            item: Instagram post dict with keys:
                - title: str (caption excerpt)
                - link: str (post URL)
                - raw_summary: str (full caption)
                - source: str (e.g., "Instagram (@username)")
                - provider: str (INSTAGRAM)
                - published_date: datetime
                - metadata: Dict (hashtags, mentions, likes, views, comments, etc.)

        Returns:
            Tuple of (processed_data dict, dedupe_key str)
        """
        title = item.get('title', '')
        link = item.get('link', '')
        raw_summary = item.get('raw_summary', '')
        provider = item.get('provider', 'INSTAGRAM')
        source = item.get('source', provider)
        metadata = item.get('metadata', {})

        logger.info(f"Processing Instagram post from {metadata.get('owner_username', 'unknown')}")

        # Extract key data
        caption = raw_summary or title
        hashtags = metadata.get('hashtags', [])
        mentions = metadata.get('mentions', [])
        likes = metadata.get('likes', 0)
        comments = metadata.get('comments', 0)
        views = metadata.get('views', 0)
        owner_username = metadata.get('owner_username', 'unknown')

        # Step 1: Extract brands from hashtags and mentions (for tracked brands)
        brands_from_hashtags = self._extract_brands_from_hashtags(hashtags, mentions)
        logger.info(f"Brands from hashtags/mentions: {brands_from_hashtags}")

        # Step 2: Extract ALL brands from caption text using AI (if enabled)
        brands_from_ai = []
        if self.enable_ai_brand_extraction:
            if self.ai_client and len(caption.strip()) > 20:
                logger.info(f"Extracting brands from caption using AI ({len(caption)} chars)")
                try:
                    # Use Instagram-specific brand extraction (optimized for captions and @mentions)
                    ai_analysis = self.ai_client.extract_brands_from_instagram(caption)
                    brands_from_ai = ai_analysis.get('brands', [])
                    logger.info(f"AI extracted brands: {brands_from_ai}")
                except Exception as ai_error:
                    logger.warning(f"AI brand extraction failed: {ai_error}")
                    brands_from_ai = []
        else:
            logger.info("AI brand extraction disabled by config")

        # Step 3: Combine and deduplicate brands
        all_brands = brands_from_hashtags.copy()
        seen = set(b.lower() for b in all_brands)
        for brand in brands_from_ai:
            if brand.lower() not in seen:
                all_brands.append(brand)
                seen.add(brand.lower())

        logger.info(f"Combined brands (hashtags + AI): {all_brands}")
        brands_mentioned = all_brands

        # Calculate engagement metrics
        total_engagement = likes + comments
        engagement_rate = self._calculate_engagement_rate(likes, comments, views)

        # Estimate reach (use views if available, otherwise use likes as proxy)
        est_reach = views if views > 0 else likes * 10  # Rough estimate: 10x likes = reach

        # Calculate Earned Media Value (EMV)
        # Industry standard: ~$10-20 per 1000 engaged users
        emv = self._calculate_emv(total_engagement)

        logger.info(
            f"Instagram metrics - Engagement: {total_engagement}, "
            f"Rate: {engagement_rate:.2f}%, Reach: {est_reach}, EMV: ${emv:.2f}"
        )

        # Generate dedupe key
        dedupe_key = self.generate_dedupe_key(title or caption, link)

        # Build processed data (NO AI fields)
        processed_data = {
            'full_text': caption[:5000],  # Store caption
            'brands': brands_mentioned,
            'summary': f"Instagram post by @{owner_username}",  # Simple summary
            'sentiment': 'neutral',  # Default - visual content, sentiment not text-based
            'topic': 'social_media_post',  # Generic topic
            'est_reach': est_reach,
            'provider': provider,
            'source': source,
            'title': title or caption[:100],
            'link': link,
            'metadata': {
                # Engagement metrics
                'likes': likes,
                'comments': comments,
                'views': views,
                'total_engagement': total_engagement,
                'engagement_rate': engagement_rate,
                'emv': emv,

                # Influencer info
                'influencer_username': owner_username,
                'influencer_full_name': metadata.get('owner_full_name', ''),

                # Content info
                'hashtags': hashtags,
                'mentions': mentions,
                'is_video': metadata.get('is_video', False),
                'image_url': metadata.get('image_url', ''),
                'video_url': metadata.get('video_url', ''),
            }
        }

        return processed_data, dedupe_key

    def _extract_brands_from_hashtags(self, hashtags: List[str], mentions: List[str]) -> List[str]:
        """
        Extract brand names from hashtags and mentions using BrandMatcher utility.

        Args:
            hashtags: List of hashtags from the post
            mentions: List of @mentions from the post

        Returns:
            List of brand names found
        """
        if not self.brands:
            return []

        matcher = BrandMatcher(self.brands)
        return matcher.match_all(hashtags=hashtags, mentions=mentions)

    def _calculate_engagement_rate(self, likes: int, comments: int, views: int) -> float:
        """
        Calculate engagement rate

        Formula: (Likes + Comments) / Views * 100
        If views unavailable, return 0

        Args:
            likes: Number of likes
            comments: Number of comments
            views: Number of views

        Returns:
            Engagement rate as percentage
        """
        if views == 0:
            return 0.0

        total_engagement = likes + comments
        return (total_engagement / views) * 100

    def _calculate_emv(self, total_engagement: int) -> float:
        """
        Calculate Earned Media Value (EMV)

        Industry standard: ~$10-20 per 1000 engaged users
        Using $15 as middle ground

        Args:
            total_engagement: Total likes + comments + shares

        Returns:
            EMV in dollars
        """
        emv_per_1k = 15.0
        return (total_engagement / 1000) * emv_per_1k

    def get_supported_providers(self) -> List[str]:
        """Return list of providers this processor supports"""
        return ['INSTAGRAM']
