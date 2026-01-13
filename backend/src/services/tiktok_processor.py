"""
TikTok Processor - processor for TikTok videos with AI brand extraction
Combines hashtag matching with AI-powered brand detection from captions
"""
import logging
from typing import Dict, List, Tuple

from services.base_processor import BaseContentProcessor
from utils.brand_matcher import BrandMatcher
from ai_client import AIClient

logger = logging.getLogger(__name__)


class TikTokProcessor(BaseContentProcessor):
    """
    Processor for TikTok videos with AI brand extraction

    Focuses on:
    - AI brand extraction from captions (finds ALL brands)
    - Hashtag/mention brand matching (for tracked brands)
    - Engagement metrics (likes, comments, shares, views)
    - Influencer identification
    - EMV calculation
    - Viral potential scoring

    Skips:
    - AI sentiment analysis (video content, not text-heavy)
    - AI summarization (captions are already short)
    - Topic classification (already filtered by hashtag/keyword)
    """

    def __init__(self, ai_client: AIClient, brands: List[str] = None, config: Dict = None):
        """
        Initialize TikTok processor

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
        Process a TikTok video item

        Args:
            item: TikTok video dict with keys:
                - title: str (caption excerpt)
                - link: str (video URL)
                - raw_summary: str (full caption + stats)
                - source: str (e.g., "TikTok (@username)")
                - provider: str (TikTok)
                - username: str
                - nickname: str
                - stats: Dict (plays, likes, comments, shares)
                - hashtags: List[str]
                - est_reach: int

        Returns:
            Tuple of (processed_data dict, dedupe_key str)
        """
        title = item.get('title', '')
        link = item.get('link', '')
        raw_summary = item.get('raw_summary', '')
        provider = item.get('provider', 'TikTok')
        source = item.get('source', provider)
        username = item.get('username', 'unknown')
        nickname = item.get('nickname', username)
        stats = item.get('stats', {})
        hashtags = item.get('hashtags', [])
        est_reach = item.get('est_reach', 0)

        logger.info(f"Processing TikTok video from @{username}")

        # Extract engagement metrics
        plays = stats.get('plays', 0)
        likes = stats.get('likes', 0)
        comments = stats.get('comments', 0)
        shares = stats.get('shares', 0)

        # Step 1: Extract brands from hashtags (for tracked brands)
        brands_from_hashtags = self._extract_brands_from_hashtags(hashtags)
        logger.info(f"Brands from hashtags: {brands_from_hashtags}")

        # Step 2: Extract ALL brands from caption text using AI (if enabled)
        brands_from_ai = []
        if self.enable_ai_brand_extraction:
            caption_text = title + '\n' + raw_summary if raw_summary else title

            if self.ai_client and len(caption_text.strip()) > 20:
                logger.info(f"Extracting brands from caption using AI ({len(caption_text)} chars)")
                try:
                    # Use TikTok-specific brand extraction (optimized for short captions)
                    ai_analysis = self.ai_client.extract_brands_from_tiktok(caption_text)
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
        total_engagement = likes + comments + shares
        engagement_rate = self._calculate_engagement_rate(likes, comments, shares, plays)

        # Calculate Earned Media Value (EMV)
        # TikTok EMV slightly higher than Instagram due to higher shareability
        emv = self._calculate_emv(total_engagement, is_video=True)

        # Calculate viral potential score (0-100)
        viral_score = self._calculate_viral_score(plays, likes, comments, shares)

        logger.info(
            f"TikTok metrics - Engagement: {total_engagement}, "
            f"Rate: {engagement_rate:.2f}%, Reach: {est_reach}, EMV: ${emv:.2f}, "
            f"Viral Score: {viral_score}"
        )

        # Generate dedupe key
        dedupe_key = self.generate_dedupe_key(title or raw_summary, link)

        # Build processed data (NO AI fields)
        processed_data = {
            'full_text': raw_summary[:5000],  # Store caption + stats
            'brands': brands_mentioned,
            'summary': f"TikTok video by @{username}",  # Simple summary
            'sentiment': 'neutral',  # Default - video content, sentiment not text-based
            'topic': 'social_media_video',  # Generic topic
            'est_reach': est_reach,
            'provider': provider,
            'source': source,
            'title': title or raw_summary[:100],
            'link': link,
            'metadata': {
                # Engagement metrics
                'plays': plays,
                'likes': likes,
                'comments': comments,
                'shares': shares,
                'total_engagement': total_engagement,
                'engagement_rate': engagement_rate,
                'emv': emv,
                'viral_score': viral_score,

                # Influencer info
                'influencer_username': username,
                'influencer_nickname': nickname,

                # Content info
                'hashtags': hashtags,
                'video_id': item.get('video_id', ''),
            }
        }

        return processed_data, dedupe_key

    def _extract_brands_from_hashtags(self, hashtags: List[str]) -> List[str]:
        """
        Extract brand names from hashtags using BrandMatcher utility.

        Args:
            hashtags: List of hashtags from the video

        Returns:
            List of brand names found
        """
        if not self.brands:
            return []

        matcher = BrandMatcher(self.brands)
        return matcher.match_in_hashtags(hashtags)

    def _calculate_engagement_rate(self, likes: int, comments: int, shares: int, plays: int) -> float:
        """
        Calculate engagement rate for TikTok

        Formula: (Likes + Comments + Shares) / Plays * 100
        If plays unavailable, return 0

        Args:
            likes: Number of likes
            comments: Number of comments
            shares: Number of shares
            plays: Number of plays/views

        Returns:
            Engagement rate as percentage
        """
        if plays == 0:
            return 0.0

        total_engagement = likes + comments + shares
        return (total_engagement / plays) * 100

    def _calculate_emv(self, total_engagement: int, is_video: bool = True) -> float:
        """
        Calculate Earned Media Value (EMV)

        TikTok videos have higher EMV than static posts due to shareability
        Industry standard: ~$15-25 per 1000 engaged users for video content
        Using $20 for TikTok

        Args:
            total_engagement: Total likes + comments + shares
            is_video: Whether content is video (higher EMV)

        Returns:
            EMV in dollars
        """
        emv_per_1k = 20.0 if is_video else 15.0
        return (total_engagement / 1000) * emv_per_1k

    def _calculate_viral_score(self, plays: int, likes: int, comments: int, shares: int) -> int:
        """
        Calculate viral potential score (0-100)

        Factors:
        - Raw numbers (plays, likes)
        - Engagement rate
        - Share rate (most important for virality)

        Args:
            plays: Number of views
            likes: Number of likes
            comments: Number of comments
            shares: Number of shares

        Returns:
            Viral score from 0-100
        """
        if plays == 0:
            return 0

        # Calculate rates
        like_rate = likes / plays
        comment_rate = comments / plays
        share_rate = shares / plays  # Most important for virality

        # Weighted scoring (shares matter most)
        score = 0

        # Share rate (50 points max) - shares are key to virality
        if share_rate >= 0.10:  # 10% share rate = viral
            score += 50
        else:
            score += int((share_rate / 0.10) * 50)

        # Like rate (30 points max)
        if like_rate >= 0.15:  # 15% like rate = excellent
            score += 30
        else:
            score += int((like_rate / 0.15) * 30)

        # Comment rate (20 points max)
        if comment_rate >= 0.05:  # 5% comment rate = highly engaged
            score += 20
        else:
            score += int((comment_rate / 0.05) * 20)

        return min(score, 100)

    def get_supported_providers(self) -> List[str]:
        """Return list of providers this processor supports"""
        return ['TikTok']
