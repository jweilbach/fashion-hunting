# providers/youtube_provider.py
"""
YouTube Provider - fetches videos from YouTube using Apify

Uses Apify Actor: apify/youtube-scraper
Supports: channel videos, keyword search, video details, comments
"""

import os
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from .base_provider import ContentProvider
from apify_client import ApifyClient
from constants import ProviderType

logger = logging.getLogger(__name__)


class YouTubeProvider(ContentProvider):
    """
    Provider for YouTube videos using Apify scraper.
    Fetches videos based on channels, keywords, or direct video URLs.
    """

    def __init__(self, search_configs: List[Dict]):
        """
        Initialize YouTube provider.

        Args:
            search_configs: List of search config dicts with keys:
                - type: 'channel', 'search', or 'video'
                - value: channel ID/URL, search keyword, or video URL
                - count (optional): number of videos to fetch (default 20)
        """
        self.search_configs = search_configs

        api_token = os.getenv('APIFY_API_TOKEN')
        if not api_token:
            raise ValueError("APIFY_API_TOKEN environment variable is required")

        self.client = ApifyClient(api_token)
        # Using bernardo/youtube-scraper - this actor has better description support
        # Note: streamers/youtube-scraper truncates descriptions
        # We could also try: "bernardo/youtube-scraper", "curious_coder/youtube-scraper"
        self.actor_id = "bernardo/youtube-scraper"

        logging.info(
            "YouTubeProvider initialized with %d searches using Apify",
            len(search_configs)
        )

    def _search_videos(self, keyword: str, count: int = 20) -> List[Dict]:
        """Search YouTube videos by keyword using Apify"""
        logging.info(f"Searching YouTube for keyword: {keyword}")

        run_input = {
            "searchKeywords": keyword,
            "maxResults": min(count, 100),
        }

        try:
            run = self.client.actor(self.actor_id).call(run_input=run_input)
            items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
            logging.info(f"Found {len(items)} videos for keyword: {keyword}")
            return [self._normalize_video_data(item) for item in items]
        except Exception as e:
            logging.error(f"Error searching YouTube for '{keyword}': {e}")
            return []

    def _get_channel_videos(self, channel_url: str, count: int = 20) -> List[Dict]:
        """Fetch videos from a specific YouTube channel using Apify"""
        logging.info(f"Fetching videos from channel: {channel_url}")

        run_input = {
            "startUrls": [{"url": channel_url}],
            "maxResults": min(count, 100),
        }

        try:
            run = self.client.actor(self.actor_id).call(run_input=run_input)
            items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
            logging.info(f"Found {len(items)} videos from channel")
            return [self._normalize_video_data(item) for item in items]
        except Exception as e:
            logging.error(f"Error fetching channel videos: {e}")
            return []

    def _get_video_details(self, video_url: str) -> Optional[Dict]:
        """Fetch details for a specific YouTube video using Apify"""
        logging.info(f"Fetching video details: {video_url}")

        run_input = {
            "startUrls": [{"url": video_url}],
            "maxResults": 1,
        }

        try:
            run = self.client.actor(self.actor_id).call(run_input=run_input)
            items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
            if items:
                return self._normalize_video_data(items[0])
            return None
        except Exception as e:
            logging.error(f"Error fetching video details: {e}")
            return None

    def _normalize_video_data(self, video: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize YouTube video data from Apify to standard format"""
        # Log all available fields to debug description issue
        logger.info(f"Raw video data keys: {list(video.keys())}")

        video_id = video.get('id', '')
        title = video.get('title', '')
        description = video.get('description', '') or video.get('text', '')  # Try 'text' field too
        channel_name = video.get('channelName', 'Unknown')
        channel_id = video.get('channelId', '')

        logger.info(f"Video: {title[:50]}... | Description length: {len(description)}")

        # URL
        video_url = video.get('url') or f"https://www.youtube.com/watch?v={video_id}"

        # Stats - get from correct field names (Apify returns them here)
        # Note: Apify uses 'viewCount', 'commentsCount' (not 'views', 'numberOfComments')
        views = int(video.get('viewCount', 0))
        likes = int(video.get('likes', 0))
        comments = int(video.get('commentsCount', 0))

        # Debug logging to see what fields are available when views is 0
        if views == 0 and (likes > 0 or comments > 0):
            logging.warning(
                f"YouTube video has engagement but 0 views. "
                f"Raw viewCount field: {video.get('viewCount')}, "
                f"Available keys: {list(video.keys())[:20]}..."  # Limit output
            )

        # Date
        published_date = video.get('date')
        if published_date:
            try:
                # Try to parse ISO date
                published_dt = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                published_date = published_dt.isoformat()
            except:
                pass

        stats_text = (
            f"[👁️ {self._format_number(views)} | "
            f"❤️ {self._format_number(likes)} | "
            f"💬 {self._format_number(comments)}]"
        )
        raw_summary = f"{description[:500]}\n\n{stats_text}".strip()

        return {
            'source': f"YouTube ({channel_name})",
            'title': title,
            'link': video_url,
            'raw_summary': raw_summary,
            'provider': 'YouTube',
            'video_id': video_id,
            'channel_name': channel_name,
            'channel_id': channel_id,
            'description': description,
            'stats': {
                'views': views,
                'likes': likes,
                'comments': comments,
            },
            'est_reach': views,
            'published_date': published_date,
            'duration': video.get('duration', ''),
            'thumbnail_url': video.get('thumbnailUrl', ''),
        }

    def _format_number(self, num: int) -> str:
        """Format large numbers with K/M/B suffixes"""
        if num >= 1_000_000_000:
            return f"{num/1_000_000_000:.1f}B"
        if num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        if num >= 1_000:
            return f"{num/1_000:.1f}K"
        return str(num)

    def fetch_items(self) -> List[Dict]:
        """Fetch all YouTube videos based on search configurations"""
        all_videos: List[Dict] = []

        for config in self.search_configs:
            search_type = config.get('type', 'search')
            value = config.get('value', '')
            count = int(config.get('count', 20))

            if not value:
                logging.warning(f"Skipping empty search config: {config}")
                continue

            if search_type == 'search':
                vids = self._search_videos(value, count)
            elif search_type == 'channel':
                vids = self._get_channel_videos(value, count)
            elif search_type == 'video':
                vid = self._get_video_details(value)
                vids = [vid] if vid else []
            else:
                logging.warning(f"Unknown search type: {search_type}")
                continue

            all_videos.extend(vids)

        logging.info(f"YouTubeProvider: Fetched {len(all_videos)} total videos")
        return all_videos

    def get_provider_name(self) -> str:
        return ProviderType.YOUTUBE

    # ==========================================
    # Brand 360 Extended Interface Methods
    # ==========================================

    @classmethod
    def get_display_name(cls) -> str:
        return "YouTube"

    @classmethod
    def get_search_types(cls) -> List[Dict]:
        return [
            {'value': 'channel', 'label': 'Channel'},
            {'value': 'search', 'label': 'Search'},
            {'value': 'video', 'label': 'Video'},
        ]

    @classmethod
    def requires_handle(cls) -> bool:
        return True  # Channel ID or handle

    @classmethod
    def get_handle_placeholder(cls) -> str:
        return "UCxxxx or @handle"

    @classmethod
    def get_handle_label(cls) -> str:
        return "Channel ID/Handle"

    @classmethod
    def is_social_media(cls) -> bool:
        return True

    @classmethod
    def get_provider_type_value(cls) -> str:
        return ProviderType.YOUTUBE
