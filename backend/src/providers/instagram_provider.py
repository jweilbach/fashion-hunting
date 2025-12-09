# providers/instagram_provider.py
"""
Instagram Provider - fetches Instagram posts using Apify
"""

import logging
from typing import List, Dict, Optional
from .base_provider import ContentProvider
from services.apify_scraper_service import ApifyScraperService
from constants import ProviderType

logger = logging.getLogger(__name__)


class InstagramProvider(ContentProvider):
    """
    Provider for Instagram content via Apify.

    Supports:
    - Brand mention searches
    - Profile scraping
    - Hashtag scraping
    """

    def __init__(
        self,
        search_type: str,  # 'mentions', 'profile', 'hashtag'
        search_value: str,  # brand name, username, or hashtag
        max_posts: int = 50
    ):
        """
        Initialize Instagram provider.

        Args:
            search_type: Type of search ('mentions', 'profile', 'hashtag')
            search_value: Value to search for
            max_posts: Maximum number of posts to fetch
        """
        self.search_type = search_type
        self.search_value = search_value
        self.max_posts = max_posts

        logger.info(
            f"InstagramProvider initialized - type: {search_type}, "
            f"value: {search_value}, max: {max_posts}"
        )

    def fetch_items(self) -> List[Dict]:
        """
        Fetch Instagram posts based on configured search type.

        Returns:
            List of standardized item dicts matching ContentProvider format
        """
        try:
            # Initialize Apify scraper
            scraper = ApifyScraperService()

            # Fetch posts based on search type
            if self.search_type == 'mentions':
                logger.info(f"Searching Instagram for brand mentions: {self.search_value}")
                posts = scraper.scrape_instagram_mentions(
                    brand_name=self.search_value,
                    max_posts=self.max_posts
                )

            elif self.search_type == 'profile':
                logger.info(f"Scraping Instagram profile: @{self.search_value}")
                posts = scraper.scrape_instagram_profile(
                    username=self.search_value,
                    max_posts=self.max_posts
                )

            elif self.search_type == 'hashtag':
                logger.info(f"Scraping Instagram hashtag: #{self.search_value}")
                posts = scraper.scrape_instagram_hashtag(
                    hashtag=self.search_value,
                    max_posts=self.max_posts
                )

            else:
                raise ValueError(f"Invalid search_type: {self.search_type}")

            logger.info(f"✅ Fetched {len(posts)} Instagram posts")
            return posts

        except Exception as e:
            logger.error(f"Error fetching Instagram content: {e}", exc_info=True)
            return []

    def get_provider_name(self) -> str:
        """Return the name of this provider"""
        return ProviderType.INSTAGRAM
