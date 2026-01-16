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

    def __init__(self, search_configs: List[Dict]):
        """
        Initialize Instagram provider.

        Args:
            search_configs: List of search config dicts with keys:
                - type: 'mentions', 'profile', 'hashtag', or 'user'
                - value: brand name, username, or hashtag
                - count (optional): number of posts to fetch (default 50)

        Example:
            >>> configs = [
            ...     {'type': 'hashtag', 'value': 'fashion', 'count': 30},
            ...     {'type': 'user', 'value': 'fashionista', 'count': 20}
            ... ]
            >>> provider = InstagramProvider(configs)
        """
        self.search_configs = search_configs

        logger.info(
            f"InstagramProvider initialized with {len(search_configs)} searches"
        )

    def fetch_items(self) -> List[Dict]:
        """
        Fetch Instagram posts based on configured searches.

        Returns:
            List of standardized item dicts matching ContentProvider format
        """
        all_posts: List[Dict] = []

        for config in self.search_configs:
            search_type = config.get('type', 'hashtag')
            value = config.get('value', '')
            count = int(config.get('count', 50))

            if not value:
                logger.warning(f"Skipping empty search config: {config}")
                continue

            try:
                # Initialize Apify scraper
                scraper = ApifyScraperService()

                # Map 'user' to 'profile' for backwards compatibility
                if search_type == 'user':
                    search_type = 'profile'

                # Fetch posts based on search type
                if search_type == 'mentions':
                    logger.info(f"Searching Instagram for brand mentions: {value}")
                    posts = scraper.scrape_instagram_mentions(
                        brand_name=value,
                        max_posts=count
                    )

                elif search_type == 'profile':
                    logger.info(f"Scraping Instagram profile: @{value}")
                    posts = scraper.scrape_instagram_profile(
                        username=value,
                        max_posts=count
                    )

                elif search_type == 'hashtag':
                    logger.info(f"Scraping Instagram hashtag: #{value}")
                    posts = scraper.scrape_instagram_hashtag(
                        hashtag=value,
                        max_posts=count
                    )

                else:
                    logger.warning(f"Unknown search type: {search_type}")
                    continue

                logger.info(f"Fetched {len(posts)} posts for {search_type}: {value}")
                all_posts.extend(posts)

            except Exception as e:
                logger.error(f"Error fetching Instagram {search_type} '{value}': {e}", exc_info=True)
                continue

        logger.info(f"InstagramProvider: Fetched {len(all_posts)} total posts")
        return all_posts

    def get_provider_name(self) -> str:
        """Return the name of this provider"""
        return ProviderType.INSTAGRAM

    # ==========================================
    # Brand 360 Extended Interface Methods
    # ==========================================

    @classmethod
    def get_display_name(cls) -> str:
        return "Instagram"

    @classmethod
    def get_search_types(cls) -> List[Dict]:
        return [
            {'value': 'profile', 'label': 'Profile'},
            {'value': 'hashtag', 'label': 'Hashtag'},
            {'value': 'mentions', 'label': 'Mentions'},
        ]

    @classmethod
    def requires_handle(cls) -> bool:
        return True

    @classmethod
    def get_handle_placeholder(cls) -> str:
        return "@username"

    @classmethod
    def get_handle_label(cls) -> str:
        return "Instagram Handle"

    @classmethod
    def is_social_media(cls) -> bool:
        return True

    @classmethod
    def get_provider_type_value(cls) -> str:
        return ProviderType.INSTAGRAM
