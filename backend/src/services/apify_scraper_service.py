"""
Apify Scraper Service - Integrates with Apify API for social media scraping

This service provides a unified interface to scrape social media platforms using
Apify's Actor ecosystem. It handles:
- Instagram profile/hashtag scraping
- TikTok profile/hashtag scraping
- LinkedIn profile/post scraping
- YouTube channel/search scraping

Each platform returns normalized data that can be processed by SocialMediaProcessor.
"""
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from apify_client import ApifyClient

logger = logging.getLogger(__name__)


class ApifyScraperService:
    """
    Service for scraping social media platforms using Apify Actors

    Supported platforms:
    - Instagram: Profile posts, hashtag search, mentions
    - TikTok: Profile videos, hashtag search
    - LinkedIn: Profile posts, company posts
    - YouTube: Channel videos, search results
    """

    # Apify Actor IDs for different platforms
    ACTORS = {
        'instagram': 'apify/instagram-scraper',
        'tiktok': 'clockworks/tiktok-scraper',
        'linkedin': 'voyager/linkedin-profile-scraper',
        'youtube': 'streamers/youtube-scraper',
    }

    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize Apify client

        Args:
            api_token: Apify API token (defaults to APIFY_API_TOKEN env var)
        """
        self.api_token = api_token or os.getenv('APIFY_API_TOKEN')
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN not found in environment or constructor")

        self.client = ApifyClient(self.api_token)
        logger.info("✅ Apify client initialized")

    def scrape_instagram_profile(
        self,
        username: str,
        max_posts: int = 50,
        search_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape Instagram profile posts

        Args:
            username: Instagram username (without @)
            max_posts: Maximum number of posts to retrieve
            search_query: Optional search query to filter posts (e.g., brand name)

        Returns:
            List of normalized post dictionaries
        """
        logger.info(f"🔍 Scraping Instagram profile: @{username} (max {max_posts} posts)")

        # Use direct URL format (required by Apify Instagram Actor)
        profile_url = f"https://www.instagram.com/{username}/"

        # Configure the Actor input with directUrls
        run_input = {
            "directUrls": [profile_url],
            "resultsLimit": max_posts,
        }

        logger.info(f"   Using direct URL: {profile_url}")

        # Run the Actor and wait for it to finish
        run = self.client.actor(self.ACTORS['instagram']).call(run_input=run_input)

        # Fetch results from the dataset
        items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
        logger.info(f"✅ Scraped {len(items)} Instagram posts from @{username}")

        # Normalize the data to our format
        normalized_posts = []
        for item in items:
            # Skip error items from Apify
            if 'error' in item:
                logger.warning(f"Skipping Instagram item with error: {item.get('error')} - {item.get('errorDescription')}")
                continue
            normalized_posts.append(self._normalize_instagram_post(item))

        logger.info(f"✅ Successfully normalized {len(normalized_posts)} Instagram posts (skipped {len(items) - len(normalized_posts)} errors)")
        return normalized_posts

    def scrape_instagram_hashtag(
        self,
        hashtag: str,
        max_posts: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Scrape Instagram hashtag posts

        Args:
            hashtag: Hashtag to search (without #)
            max_posts: Maximum number of posts to retrieve

        Returns:
            List of normalized post dictionaries
        """
        logger.info(f"🔍 Scraping Instagram hashtag: #{hashtag} (max {max_posts} posts)")

        # Use direct URL format (required by Apify Instagram Actor)
        hashtag_url = f"https://www.instagram.com/explore/tags/{hashtag}/"

        run_input = {
            "directUrls": [hashtag_url],
            "resultsLimit": max_posts,
        }

        logger.info(f"   Using direct URL: {hashtag_url}")

        run = self.client.actor(self.ACTORS['instagram']).call(run_input=run_input)
        items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())

        logger.info(f"✅ Scraped {len(items)} posts for #{hashtag}")

        normalized_posts = []
        for item in items:
            # Skip error items from Apify
            if 'error' in item:
                logger.warning(f"Skipping Instagram item with error: {item.get('error')} - {item.get('errorDescription')}")
                continue
            normalized_posts.append(self._normalize_instagram_post(item))

        logger.info(f"✅ Successfully normalized {len(normalized_posts)} Instagram posts (skipped {len(items) - len(normalized_posts)} errors)")
        return normalized_posts

    def scrape_instagram_mentions(
        self,
        brand_name: str,
        max_posts: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search Instagram for posts mentioning a brand

        Note: Uses hashtag search as workaround since Instagram Actor doesn't
        support keyword search. Searches for #{brand_name} hashtag.

        Args:
            brand_name: Brand name to search for (will be used as hashtag)
            max_posts: Maximum number of posts to retrieve

        Returns:
            List of normalized post dictionaries
        """
        logger.info(f"🔍 Searching Instagram for hashtag: #{brand_name}")

        # Use direct URL format (required by Apify Instagram Actor)
        hashtag_url = f"https://www.instagram.com/explore/tags/{brand_name}/"

        run_input = {
            "directUrls": [hashtag_url],
            "resultsLimit": max_posts,
        }

        logger.info(f"   Using direct URL: {hashtag_url}")

        run = self.client.actor(self.ACTORS['instagram']).call(run_input=run_input)
        items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())

        logger.info(f"✅ Found {len(items)} Instagram posts for #{brand_name}")

        # Debug: Log first item structure
        if items:
            logger.info(f"📊 Sample Instagram post fields: {list(items[0].keys())}")
            if 'error' in items[0]:
                logger.warning(f"⚠️ Apify returned error: {items[0].get('error')} - {items[0].get('errorDescription')}")

        normalized_posts = []
        for item in items:
            # Skip error items from Apify
            if 'error' in item:
                logger.warning(f"Skipping Instagram item with error: {item.get('error')} - {item.get('errorDescription')}")
                continue

            normalized_posts.append(self._normalize_instagram_post(item))

        logger.info(f"✅ Successfully normalized {len(normalized_posts)} Instagram posts (skipped {len(items) - len(normalized_posts)} errors)")
        return normalized_posts

    def _normalize_instagram_post(self, raw_post: Dict) -> Dict[str, Any]:
        """
        Normalize Instagram post data to our standard format

        Args:
            raw_post: Raw post data from Apify Instagram Actor

        Returns:
            Normalized post dictionary matching our schema
        """
        # Extract timestamp
        timestamp = raw_post.get('timestamp')
        if timestamp:
            try:
                published_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                published_date = datetime.now()
        else:
            published_date = datetime.now()

        # Build normalized post
        normalized = {
            'title': raw_post.get('caption', '')[:500],  # Use caption as title
            'link': raw_post.get('url', ''),
            'raw_summary': raw_post.get('caption', ''),  # Full caption
            'source': f"Instagram (@{raw_post.get('ownerUsername', 'unknown')})",
            'provider': 'INSTAGRAM',
            'published_date': published_date,
            'metadata': {
                'hashtags': raw_post.get('hashtags', []),
                'mentions': raw_post.get('mentions', []),
                'likes': raw_post.get('likesCount', 0),
                'views': raw_post.get('videoViewCount', 0),
                'comments': raw_post.get('commentsCount', 0),
                'image_url': raw_post.get('displayUrl', ''),
                'video_url': raw_post.get('videoUrl', ''),
                'is_video': raw_post.get('type') == 'Video',
                'owner_username': raw_post.get('ownerUsername', ''),
                'owner_full_name': raw_post.get('ownerFullName', ''),
            }
        }

        return normalized

    def scrape_tiktok_profile(
        self,
        username: str,
        max_videos: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Scrape TikTok profile videos

        Args:
            username: TikTok username (without @)
            max_videos: Maximum number of videos to retrieve

        Returns:
            List of normalized video dictionaries
        """
        logger.info(f"🔍 Scraping TikTok profile: @{username} (max {max_videos} videos)")

        run_input = {
            "profiles": [username],
            "resultsPerPage": max_videos,
        }

        run = self.client.actor(self.ACTORS['tiktok']).call(run_input=run_input)
        items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())

        logger.info(f"✅ Scraped {len(items)} TikTok videos from @{username}")

        normalized_videos = []
        for item in items:
            normalized_videos.append(self._normalize_tiktok_video(item))

        return normalized_videos

    def scrape_tiktok_hashtag(
        self,
        hashtag: str,
        max_videos: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Scrape TikTok hashtag videos

        Args:
            hashtag: Hashtag to search (without #)
            max_videos: Maximum number of videos to retrieve

        Returns:
            List of normalized video dictionaries
        """
        logger.info(f"🔍 Scraping TikTok hashtag: #{hashtag} (max {max_videos} videos)")

        run_input = {
            "hashtags": [hashtag],
            "resultsPerPage": max_videos,
        }

        run = self.client.actor(self.ACTORS['tiktok']).call(run_input=run_input)
        items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())

        logger.info(f"✅ Scraped {len(items)} TikTok videos for #{hashtag}")

        normalized_videos = []
        for item in items:
            normalized_videos.append(self._normalize_tiktok_video(item))

        return normalized_videos

    def _normalize_tiktok_video(self, raw_video: Dict) -> Dict[str, Any]:
        """
        Normalize TikTok video data to our standard format

        Args:
            raw_video: Raw video data from Apify TikTok Actor

        Returns:
            Normalized video dictionary matching our schema
        """
        # Extract timestamp
        create_time = raw_video.get('createTime')
        if create_time:
            try:
                published_date = datetime.fromtimestamp(create_time)
            except:
                published_date = datetime.now()
        else:
            published_date = datetime.now()

        # Build normalized video
        normalized = {
            'title': raw_video.get('text', '')[:500],  # Use description as title
            'link': raw_video.get('webVideoUrl', ''),
            'raw_summary': raw_video.get('text', ''),  # Full description
            'source': f"TikTok (@{raw_video.get('authorMeta', {}).get('name', 'unknown')})",
            'provider': 'TIKTOK',
            'published_date': published_date,
            'metadata': {
                'hashtags': [tag.get('name', '') for tag in raw_video.get('hashtags', [])],
                'mentions': raw_video.get('mentions', []),
                'likes': raw_video.get('diggCount', 0),
                'views': raw_video.get('playCount', 0),
                'comments': raw_video.get('commentCount', 0),
                'shares': raw_video.get('shareCount', 0),
                'video_url': raw_video.get('videoUrl', ''),
                'cover_url': raw_video.get('covers', {}).get('default', ''),
                'music': raw_video.get('musicMeta', {}).get('musicName', ''),
                'author_username': raw_video.get('authorMeta', {}).get('name', ''),
                'author_nickname': raw_video.get('authorMeta', {}).get('nickName', ''),
            }
        }

        return normalized

    def test_connection(self) -> bool:
        """
        Test the Apify API connection

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to get user info to verify token
            user_info = self.client.user().get()
            logger.info(f"✅ Apify connection successful! User: {user_info.get('username', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"❌ Apify connection failed: {str(e)}")
            return False
