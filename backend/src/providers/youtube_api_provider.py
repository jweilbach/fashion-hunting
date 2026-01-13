# providers/youtube_api_provider.py
"""
YouTube API Provider - fetches videos from YouTube using official YouTube Data API v3

Uses: Google YouTube Data API v3
Supports: channel videos, keyword search, video details
Returns: Full video descriptions (not truncated like Apify scrapers)
Free Tier: 10,000 quota units/day (enough for ~83 jobs with 20 videos each)
"""

import os
import logging
from typing import List, Dict, Optional
from datetime import datetime
from .base_provider import ContentProvider
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from constants import ProviderType

logger = logging.getLogger(__name__)


class YouTubeAPIProvider(ContentProvider):
    """
    Provider for YouTube videos using official YouTube Data API v3.
    Fetches videos with full descriptions based on channels, keywords, or direct video URLs.
    """

    def __init__(self, search_configs: List[Dict]):
        """
        Initialize YouTube API provider.

        Args:
            search_configs: List of search config dicts with keys:
                - type: 'channel', 'search', or 'video'
                - value: channel ID/URL, search keyword, or video ID
                - count (optional): number of videos to fetch (default 20, max 50)

        Environment Variables:
            YOUTUBE_API_KEY: YouTube Data API v3 key (required)
        """
        self.search_configs = search_configs

        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            raise ValueError("YOUTUBE_API_KEY environment variable is required")

        # Build YouTube API client
        self.youtube = build('youtube', 'v3', developerKey=api_key)

        logger.info(
            "YouTubeAPIProvider initialized with %d searches using YouTube Data API v3",
            len(search_configs)
        )

    def _search_videos(self, keyword: str, count: int = 20) -> List[Dict]:
        """
        Search YouTube videos by keyword using YouTube Data API v3

        Quota Cost: 100 units for search + 1 unit per video details call
        """
        logger.info(f"Searching YouTube for keyword: {keyword}")
        count = min(count, 50)  # API max per request

        try:
            # Step 1: Search for videos (100 quota units)
            search_response = self.youtube.search().list(
                q=keyword,
                part='snippet',
                type='video',
                maxResults=count,
                order='relevance',
                videoDuration='any'
            ).execute()

            video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]

            if not video_ids:
                logger.info(f"No videos found for keyword: {keyword}")
                return []

            # Step 2: Get full video details including full descriptions (1 quota unit per video)
            return self._get_videos_details(video_ids)

        except HttpError as e:
            logger.error(f"YouTube API error searching for '{keyword}': {e}")
            return []
        except Exception as e:
            logger.error(f"Error searching YouTube for '{keyword}': {e}")
            return []

    def _get_channel_videos(self, channel_identifier: str, count: int = 20) -> List[Dict]:
        """
        Fetch videos from a specific YouTube channel using YouTube Data API v3

        Quota Cost: 1 unit for channel lookup + 5 units for playlist items + 1 unit per video details
        """
        logger.info(f"Fetching videos from channel: {channel_identifier}")
        count = min(count, 50)

        try:
            # Extract channel ID from URL if needed
            channel_id = self._extract_channel_id(channel_identifier)

            # Step 1: Get channel's uploads playlist ID (1 quota unit)
            channel_response = self.youtube.channels().list(
                part='contentDetails',
                id=channel_id
            ).execute()

            if not channel_response.get('items'):
                logger.error(f"Channel not found: {channel_id}")
                return []

            uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

            # Step 2: Get videos from uploads playlist (5 quota units)
            playlist_response = self.youtube.playlistItems().list(
                part='contentDetails',
                playlistId=uploads_playlist_id,
                maxResults=count
            ).execute()

            video_ids = [item['contentDetails']['videoId'] for item in playlist_response.get('items', [])]

            if not video_ids:
                logger.info(f"No videos found in channel: {channel_id}")
                return []

            # Step 3: Get full video details (1 quota unit per video)
            return self._get_videos_details(video_ids)

        except HttpError as e:
            logger.error(f"YouTube API error fetching channel videos: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching channel videos: {e}")
            return []

    def _get_video_details(self, video_id: str) -> Optional[Dict]:
        """
        Fetch details for a specific YouTube video

        Quota Cost: 1 unit
        """
        logger.info(f"Fetching video details: {video_id}")

        videos = self._get_videos_details([video_id])
        return videos[0] if videos else None

    def _get_videos_details(self, video_ids: List[str]) -> List[Dict]:
        """
        Fetch full details for multiple videos (batch request)

        Quota Cost: 1 unit per video
        Can fetch up to 50 videos per request
        """
        if not video_ids:
            return []

        all_videos = []

        # Process in batches of 50 (API limit)
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i+50]

            try:
                videos_response = self.youtube.videos().list(
                    part='snippet,contentDetails,statistics',
                    id=','.join(batch_ids)
                ).execute()

                for item in videos_response.get('items', []):
                    normalized = self._normalize_video_data(item)
                    all_videos.append(normalized)

            except HttpError as e:
                logger.error(f"YouTube API error fetching video details: {e}")
            except Exception as e:
                logger.error(f"Error fetching video details: {e}")

        logger.info(f"Fetched details for {len(all_videos)} videos")
        return all_videos

    def _normalize_video_data(self, video: Dict) -> Dict:
        """Normalize YouTube API video data to standard format"""
        snippet = video.get('snippet', {})
        statistics = video.get('statistics', {})
        content_details = video.get('contentDetails', {})

        video_id = video.get('id', '')
        title = snippet.get('title', '')
        description = snippet.get('description', '')  # FULL description!
        channel_name = snippet.get('channelTitle', 'Unknown')
        channel_id = snippet.get('channelId', '')

        # URL
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        # Stats
        views = int(statistics.get('viewCount', 0))
        likes = int(statistics.get('likeCount', 0))
        comments = int(statistics.get('commentCount', 0))

        # Date
        published_at = snippet.get('publishedAt', '')
        published_date = published_at  # Already in ISO format

        # Duration (ISO 8601 format like PT15M30S)
        duration = content_details.get('duration', '')

        # Thumbnails
        thumbnails = snippet.get('thumbnails', {})
        thumbnail_url = (
            thumbnails.get('maxres', {}).get('url') or
            thumbnails.get('high', {}).get('url') or
            thumbnails.get('medium', {}).get('url') or
            thumbnails.get('default', {}).get('url') or
            ''
        )

        stats_text = (
            f"[👁️ {self._format_number(views)} | "
            f"❤️ {self._format_number(likes)} | "
            f"💬 {self._format_number(comments)}]"
        )
        raw_summary = f"{description[:500]}\n\n{stats_text}".strip()

        logger.info(f"Normalized video: {title[:50]}... | Description: {len(description)} chars")

        return {
            'source': f"YouTube ({channel_name})",
            'title': title,
            'link': video_url,
            'raw_summary': raw_summary,
            'provider': 'YouTube',
            'video_id': video_id,
            'channel_name': channel_name,
            'channel_id': channel_id,
            'description': description,  # Full description!
            'stats': {
                'views': views,
                'likes': likes,
                'comments': comments,
            },
            'est_reach': views,
            'published_date': published_date,
            'duration': duration,
            'thumbnail_url': thumbnail_url,
        }

    def _extract_channel_id(self, identifier: str) -> str:
        """
        Extract channel ID from various formats:
        - Direct ID: UCxxxxxx
        - URL: https://www.youtube.com/channel/UCxxxxxx
        - Custom URL: https://www.youtube.com/@username (requires API lookup)
        """
        # Already a channel ID
        if identifier.startswith('UC') and len(identifier) == 24:
            return identifier

        # Extract from URL
        if 'youtube.com/channel/' in identifier:
            return identifier.split('/channel/')[-1].split('?')[0].split('/')[0]

        # Custom URL (@username) - need to look up via API
        if identifier.startswith('@') or 'youtube.com/@' in identifier:
            username = identifier.replace('https://www.youtube.com/@', '').replace('@', '')
            try:
                response = self.youtube.channels().list(
                    part='id',
                    forUsername=username
                ).execute()
                if response.get('items'):
                    return response['items'][0]['id']
            except Exception as e:
                logger.error(f"Error looking up channel by username: {e}")

        # Assume it's a channel ID
        return identifier

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
                logger.warning(f"Skipping empty search config: {config}")
                continue

            if search_type == 'search':
                vids = self._search_videos(value, count)
            elif search_type == 'channel':
                vids = self._get_channel_videos(value, count)
            elif search_type == 'video':
                vid = self._get_video_details(value)
                vids = [vid] if vid else []
            else:
                logger.warning(f"Unknown search type: {search_type}")
                continue

            all_videos.extend(vids)

        logger.info(f"YouTubeAPIProvider: Fetched {len(all_videos)} total videos with full descriptions")
        return all_videos

    def get_provider_name(self) -> str:
        return ProviderType.YOUTUBE
