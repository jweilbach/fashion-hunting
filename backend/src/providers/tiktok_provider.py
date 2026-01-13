# providers/tiktok_provider.py
"""
TikTok Provider - fetches videos from TikTok using Apify

Uses Apify Actor: clockworks/tiktok-scraper
Supports: brand mentions, hashtag tracking, user profiles, video engagement
"""

import os
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from .base_provider import ContentProvider
from apify_client import ApifyClient
from constants import ProviderType


class TikTokProvider(ContentProvider):
    """
    Provider for TikTok videos using Apify scraper.
    Fetches videos based on hashtags, keywords, or user profiles.
    """

    def __init__(self, search_configs: List[Dict]):
        """
        Initialize TikTok provider.

        Args:
            search_configs: List of search config dicts with keys:
                - type: 'hashtag', 'keyword', or 'user'
                - value: hashtag/keyword/username to search
                - count (optional): number of videos to fetch (default 30)
        """
        self.search_configs = search_configs

        api_token = os.getenv('APIFY_API_TOKEN')
        if not api_token:
            raise ValueError("APIFY_API_TOKEN environment variable is required")

        self.client = ApifyClient(api_token)
        self.actor_id = "clockworks/tiktok-scraper"

        logging.info(
            "TikTokProvider initialized with %d searches using Apify",
            len(search_configs)
        )

    def _search_hashtag(self, hashtag: str, count: int = 30) -> List[Dict]:
        """Search TikTok by hashtag using Apify"""
        hashtag = hashtag.lstrip('#')
        logging.info("Searching TikTok hashtag: #%s", hashtag)

        run_input = {
            "hashtags": [hashtag],
            "resultsPerPage": min(count, 100),
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
        }

        try:
            run = self.client.actor(self.actor_id).call(run_input=run_input)
            items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
            logging.info("Found %d videos for #%s", len(items), hashtag)
            return [self._normalize_video_data(item) for item in items]
        except Exception as e:
            logging.error("Error searching hashtag #%s: %s", hashtag, e)
            return []

    def _search_keyword(self, keyword: str, count: int = 30) -> List[Dict]:
        """Search TikTok by keyword using Apify"""
        logging.info("Searching TikTok keyword: %s", keyword)

        run_input = {
            "searchQueries": [keyword],
            "resultsPerPage": min(count, 100),
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
        }

        try:
            run = self.client.actor(self.actor_id).call(run_input=run_input)
            items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
            logging.info("Found %d videos for keyword: %s", len(items), keyword)
            return [self._normalize_video_data(item) for item in items]
        except Exception as e:
            logging.error("Error searching keyword '%s': %s", keyword, e)
            return []

    def _get_user_videos(self, username: str, count: int = 30) -> List[Dict]:
        """Fetch videos from a specific TikTok user using Apify"""
        username = username.lstrip('@')
        logging.info("Fetching videos from user: @%s", username)

        run_input = {
            "profiles": [username],
            "resultsPerPage": min(count, 100),
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
        }

        try:
            run = self.client.actor(self.actor_id).call(run_input=run_input)
            items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
            logging.info("Found %d videos from @%s", len(items), username)
            return [self._normalize_video_data(item) for item in items]
        except Exception as e:
            logging.error("Error fetching videos from @%s: %s", username, e)
            return []

    def _normalize_video_data(self, video: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize TikTok video data from Apify to standard format"""
        author = video.get('authorMeta', {}) or {}
        username = author.get('name', 'unknown')
        nickname = author.get('nickName', username)
        video_id = video.get('id', '')
        desc = (video.get('text') or '').strip()

        # URL
        video_url = video.get('webVideoUrl') or f"https://www.tiktok.com/@{username}/video/{video_id}"

        # Hashtags
        hashtags = [f"#{tag.get('name', '')}" for tag in video.get('hashtags', [])]

        # Stats - get from top-level fields (Apify returns them here)
        play_count = int(video.get('playCount', 0))
        like_count = int(video.get('diggCount', 0))
        comment_count = int(video.get('commentCount', 0))
        share_count = int(video.get('shareCount', 0))

        # Debug logging to see what fields are available when play_count is 0
        if play_count == 0 and (like_count > 0 or comment_count > 0 or share_count > 0):
            logging.warning(
                f"TikTok video has engagement but 0 plays. "
                f"Raw playCount field: {video.get('playCount')}, "
                f"Available keys: {list(video.keys())[:20]}..."  # Limit output
            )

        stats_text = (
            f"[👁️ {self._format_number(play_count)} | "
            f"❤️ {self._format_number(like_count)} | "
            f"💬 {self._format_number(comment_count)} | "
            f"🔗 {self._format_number(share_count)}]"
        )
        hashtag_text = " ".join(hashtags) if hashtags else ""
        raw_summary = "\n\n".join(x for x in [desc, hashtag_text, stats_text] if x).strip()

        return {
            'source': f"TikTok (@{username})",
            'title': desc[:200] if desc else f"Video by @{username}",
            'link': video_url,
            'raw_summary': raw_summary,
            'provider': 'TikTok',
            'video_id': video_id,
            'username': username,
            'nickname': nickname,
            'hashtags': hashtags,
            'stats': {
                'plays': play_count,
                'likes': like_count,
                'comments': comment_count,
                'shares': share_count,
            },
            'est_reach': play_count,
            'create_time': video.get('createTime', 0),
        }

    def _format_number(self, num: int) -> str:
        if num >= 1_000_000_000:
            return f"{num/1_000_000_000:.1f}B"
        if num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        if num >= 1_000:
            return f"{num/1_000:.1f}K"
        return str(num)

    def fetch_items(self) -> List[Dict]:
        """Fetch all TikTok videos based on search configurations"""
        all_videos: List[Dict] = []

        for config in self.search_configs:
            search_type = config.get('type', 'hashtag')
            value = config.get('value', '')
            count = int(config.get('count', 30))

            if not value:
                logging.warning("Skipping empty search config: %s", config)
                continue

            if search_type == 'hashtag':
                vids = self._search_hashtag(value, count)
            elif search_type == 'keyword':
                vids = self._search_keyword(value, count)
            elif search_type == 'user':
                vids = self._get_user_videos(value, count)
            else:
                logging.warning("Unknown search type: %s", search_type)
                continue

            all_videos.extend(vids)

        logging.info("TikTokProvider: Fetched %d total videos", len(all_videos))
        return all_videos

    def get_provider_name(self) -> str:
        return ProviderType.TIKTOK
