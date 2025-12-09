"""
YouTube Processor - lightweight processor for YouTube videos
Skips AI processing and focuses on engagement metrics and content creator tracking
"""
import logging
from typing import Dict, List, Tuple

from services.base_processor import BaseContentProcessor

logger = logging.getLogger(__name__)


class YouTubeProcessor(BaseContentProcessor):
    """
    Lightweight processor for YouTube videos

    Focuses on:
    - Engagement metrics (views, likes, comments)
    - Creator/channel identification
    - Brand mention detection in titles/descriptions
    - EMV calculation
    - Engagement quality scoring

    Skips:
    - AI sentiment analysis (video content, not always text-focused)
    - AI summarization (descriptions are already summaries)
    - Topic classification (already filtered by search keyword)
    """

    def __init__(self, brands: List[str] = None, config: Dict = None):
        """
        Initialize YouTube processor

        Args:
            brands: List of brand names to track
            config: Configuration options (unused for YouTube)
        """
        # Don't pass ai_client to parent - we don't need it
        super().__init__(ai_client=None, brands=brands, config=config)

    def process_item(self, item: Dict) -> Tuple[Dict, str]:
        """
        Process a YouTube video item

        Args:
            item: YouTube video dict with keys:
                - title: str
                - link: str (video URL)
                - raw_summary: str (description + stats)
                - source: str (e.g., "YouTube (Channel Name)")
                - provider: str (YouTube)
                - video_id: str
                - channel_name: str
                - channel_id: str
                - description: str
                - stats: Dict (views, likes, comments)
                - est_reach: int

        Returns:
            Tuple of (processed_data dict, dedupe_key str)
        """
        title = item.get('title', '')
        link = item.get('link', '')
        raw_summary = item.get('raw_summary', '')
        provider = item.get('provider', 'YouTube')
        source = item.get('source', provider)
        video_id = item.get('video_id', '')
        channel_name = item.get('channel_name', 'Unknown')
        channel_id = item.get('channel_id', '')
        description = item.get('description', '')
        stats = item.get('stats', {})
        est_reach = item.get('est_reach', 0)

        logger.info(f"Processing YouTube video from {channel_name}")

        # Extract engagement metrics
        views = stats.get('views', 0)
        likes = stats.get('likes', 0)
        comments = stats.get('comments', 0)

        # Brand detection in title and description (NO AI - simple keyword matching)
        brands_mentioned = self._extract_brands_from_text(title, description)

        logger.info(f"Detected brands in title/description: {brands_mentioned}")

        # Calculate engagement metrics
        total_engagement = likes + comments
        engagement_rate = self._calculate_engagement_rate(likes, comments, views)

        # Calculate Earned Media Value (EMV)
        # YouTube EMV is moderate - more evergreen than TikTok but less than Instagram
        emv = self._calculate_emv(total_engagement, views, is_video=True)

        # Calculate engagement quality score (0-100)
        quality_score = self._calculate_quality_score(views, likes, comments)

        logger.info(
            f"YouTube metrics - Views: {views}, Engagement: {total_engagement}, "
            f"Rate: {engagement_rate:.2f}%, EMV: ${emv:.2f}, Quality: {quality_score}"
        )

        # Generate dedupe key
        dedupe_key = self.generate_dedupe_key(title, link)

        # Build processed data (NO AI fields)
        processed_data = {
            'full_text': f"{title}\n\n{description[:5000]}",  # Store title + description
            'brands': brands_mentioned,
            'summary': f"YouTube video by {channel_name}",  # Simple summary
            'sentiment': 'neutral',  # Default - video content, sentiment not always text-based
            'topic': 'video_content',  # Generic topic
            'est_reach': est_reach,
            'provider': provider,
            'source': source,
            'title': title,
            'link': link,
            'metadata': {
                # Engagement metrics
                'views': views,
                'likes': likes,
                'comments': comments,
                'total_engagement': total_engagement,
                'engagement_rate': engagement_rate,
                'emv': emv,
                'quality_score': quality_score,

                # Creator info
                'channel_name': channel_name,
                'channel_id': channel_id,
                'video_id': video_id,

                # Content info
                'description': description[:1000],  # Truncated description
                'duration': item.get('duration', ''),
                'thumbnail_url': item.get('thumbnail_url', ''),
            }
        }

        return processed_data, dedupe_key

    def _extract_brands_from_text(self, title: str, description: str) -> List[str]:
        """
        Extract brand names from title and description (NO AI - simple keyword matching)

        Args:
            title: Video title
            description: Video description

        Returns:
            List of brand names found
        """
        if not self.brands:
            return []

        import re
        brands_found = []
        combined_text = f"{title} {description}".lower()

        for brand in self.brands:
            brand_lower = brand.lower()
            # Use word boundary matching to avoid false positives
            # This prevents "color" from matching "haircolor" or "colorful"
            # Examples:
            #   - "Color Wow" → matches "color wow", "Color Wow hair", etc. ✅
            #   - "Color Wow" → does NOT match "haircolor" ❌
            #   - "Versace" → matches "Versace", "Versace style", etc. ✅
            pattern = r'\b' + re.escape(brand_lower) + r'\b'
            if re.search(pattern, combined_text):
                if brand not in brands_found:
                    brands_found.append(brand)

        return brands_found

    def _calculate_engagement_rate(self, likes: int, comments: int, views: int) -> float:
        """
        Calculate engagement rate for YouTube

        Formula: (Likes + Comments) / Views * 100
        If views = 0, return 0

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

    def _calculate_emv(self, total_engagement: int, views: int, is_video: bool = True) -> float:
        """
        Calculate Earned Media Value (EMV)

        YouTube videos have medium EMV:
        - More evergreen than TikTok (longer shelf life)
        - Less immediate engagement than Instagram
        - Higher watch time value

        Industry standard: ~$17-22 per 1000 engaged users for YouTube
        Using $18 as baseline, with bonus for high view counts

        Args:
            total_engagement: Total likes + comments
            views: Number of views
            is_video: Whether content is video (always True for YouTube)

        Returns:
            EMV in dollars
        """
        base_emv_per_1k = 18.0

        # Bonus for viral videos (>1M views = higher brand exposure value)
        if views > 1_000_000:
            emv_per_1k = base_emv_per_1k * 1.5  # 50% bonus for viral content
        elif views > 100_000:
            emv_per_1k = base_emv_per_1k * 1.2  # 20% bonus for popular content
        else:
            emv_per_1k = base_emv_per_1k

        return (total_engagement / 1000) * emv_per_1k

    def _calculate_quality_score(self, views: int, likes: int, comments: int) -> int:
        """
        Calculate content quality score (0-100)

        Factors:
        - Like rate (likes/views)
        - Comment rate (comments/views)
        - Absolute numbers (bonus for viral content)

        Args:
            views: Number of views
            likes: Number of likes
            comments: Number of comments

        Returns:
            Quality score from 0-100
        """
        if views == 0:
            return 0

        # Calculate rates
        like_rate = likes / views
        comment_rate = comments / views

        score = 0

        # Like rate (60 points max)
        # YouTube average: ~4-5% like rate
        if like_rate >= 0.10:  # 10% like rate = exceptional
            score += 60
        elif like_rate >= 0.05:  # 5% = very good
            score += 50
        elif like_rate >= 0.03:  # 3% = above average
            score += 40
        else:
            score += int((like_rate / 0.10) * 60)

        # Comment rate (30 points max)
        # YouTube average: ~0.5-1% comment rate
        if comment_rate >= 0.02:  # 2% comment rate = highly engaged
            score += 30
        elif comment_rate >= 0.01:  # 1% = good
            score += 25
        elif comment_rate >= 0.005:  # 0.5% = average
            score += 20
        else:
            score += int((comment_rate / 0.02) * 30)

        # Viral bonus (10 points max)
        if views > 10_000_000:  # 10M+ views
            score += 10
        elif views > 1_000_000:  # 1M+ views
            score += 7
        elif views > 100_000:  # 100K+ views
            score += 5
        elif views > 10_000:  # 10K+ views
            score += 3

        return min(score, 100)

    def get_supported_providers(self) -> List[str]:
        """Return list of providers this processor supports"""
        return ['YouTube']
