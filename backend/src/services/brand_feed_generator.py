"""
Brand Feed Generator Service - Auto-generates feeds from brand social profiles

When a brand is created with social profile configuration, this service
automatically creates the corresponding feed configurations for tracking.
"""
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from models.feed import FeedConfig
from models.brand import BrandConfig
from repositories.feed_repository import FeedRepository

logger = logging.getLogger(__name__)


# Provider name mapping to uppercase constants
PROVIDER_MAP = {
    'instagram': 'INSTAGRAM',
    'tiktok': 'TIKTOK',
    'youtube': 'YOUTUBE',
    'google_news': 'RSS',  # Google News uses RSS provider
    'google_search': 'GOOGLE_SEARCH',
}


class BrandFeedGenerator:
    """
    Service for auto-generating feed configurations from brand social profiles.

    When a brand is created/updated with social_profiles configuration,
    this service creates corresponding FeedConfig records.
    """

    def __init__(self, db: Session, feed_repo: Optional[FeedRepository] = None):
        """
        Initialize the brand feed generator.

        Args:
            db: SQLAlchemy database session
            feed_repo: Optional custom feed repository
        """
        self.db = db
        self.feed_repo = feed_repo or FeedRepository(db)

    def generate_feeds_for_brand(
        self,
        brand: BrandConfig,
        replace_existing: bool = False
    ) -> List[FeedConfig]:
        """
        Generate feed configurations from a brand's social profiles.

        Args:
            brand: Brand configuration with social_profiles
            replace_existing: If True, delete existing auto-generated feeds first

        Returns:
            List of created FeedConfig objects
        """
        social_profiles = brand.social_profiles or {}

        if not social_profiles:
            logger.info(f"No social profiles configured for brand {brand.brand_name}")
            return []

        # Optionally remove existing auto-generated feeds
        if replace_existing:
            self._delete_auto_generated_feeds(brand.id)

        created_feeds = []

        # Process each provider
        for provider_key, config in social_profiles.items():
            if not config or not config.get('enabled', False):
                continue

            feeds = self._generate_feeds_for_provider(
                brand=brand,
                provider_key=provider_key,
                config=config
            )
            created_feeds.extend(feeds)

        logger.info(f"Generated {len(created_feeds)} feeds for brand {brand.brand_name}")
        return created_feeds

    def _generate_feeds_for_provider(
        self,
        brand: BrandConfig,
        provider_key: str,
        config: Dict[str, Any]
    ) -> List[FeedConfig]:
        """
        Generate feeds for a specific provider based on its configuration.

        Args:
            brand: Brand configuration
            provider_key: Provider identifier (e.g., 'instagram', 'tiktok')
            config: Provider-specific configuration

        Returns:
            List of created FeedConfig objects
        """
        provider = PROVIDER_MAP.get(provider_key)
        if not provider:
            logger.warning(f"Unknown provider: {provider_key}")
            return []

        searches = config.get('searches', [])
        if not searches:
            logger.info(f"No searches configured for {provider_key}")
            return []

        created_feeds = []

        for search in searches:
            search_type = search.get('type')
            search_value = search.get('value')
            search_count = search.get('count', 5)

            if not search_type or not search_value:
                continue

            # Generate feed based on search type
            feed = self._create_feed(
                brand=brand,
                provider=provider,
                provider_key=provider_key,
                search_type=search_type,
                search_value=search_value,
                search_count=search_count,
                config=config
            )

            if feed:
                created_feeds.append(feed)

        return created_feeds

    def _create_feed(
        self,
        brand: BrandConfig,
        provider: str,
        provider_key: str,
        search_type: str,
        search_value: str,
        search_count: int,
        config: Dict[str, Any]
    ) -> Optional[FeedConfig]:
        """
        Create a single feed configuration.

        Args:
            brand: Brand configuration
            provider: Provider constant (e.g., 'INSTAGRAM')
            provider_key: Provider key (e.g., 'instagram')
            search_type: Type of search (e.g., 'hashtag', 'profile')
            search_value: Search value
            search_count: Number of items to fetch
            config: Full provider config (for handle/channel info)

        Returns:
            Created FeedConfig or None if creation failed
        """
        try:
            # Build feed value based on provider and search type
            feed_value = self._build_feed_value(
                provider_key=provider_key,
                search_type=search_type,
                search_value=search_value,
                config=config
            )

            # Build label for display
            label = self._build_feed_label(
                brand_name=brand.brand_name,
                provider_key=provider_key,
                search_type=search_type,
                search_value=search_value
            )

            feed = self.feed_repo.create(
                tenant_id=brand.tenant_id,
                provider=provider,
                feed_type=search_type,
                feed_value=feed_value,
                fetch_count=search_count,
                enabled=True,
                brand_id=brand.id,
                is_auto_generated=True,
                label=label,
                config={
                    'brand_name': brand.brand_name,
                    'provider_key': provider_key,
                    'search_type': search_type,
                    'search_value': search_value,
                }
            )

            logger.debug(f"Created feed: {label}")
            return feed

        except Exception as e:
            logger.error(f"Failed to create feed for {provider_key}/{search_type}: {e}")
            return None

    def _build_feed_value(
        self,
        provider_key: str,
        search_type: str,
        search_value: str,
        config: Dict[str, Any]
    ) -> str:
        """
        Build the feed_value based on provider and search type.

        Different providers expect different feed_value formats.
        """
        # Instagram
        if provider_key == 'instagram':
            if search_type == 'profile':
                handle = config.get('handle', search_value)
                return handle.lstrip('@')
            elif search_type == 'hashtag':
                return search_value.lstrip('#')
            elif search_type == 'mentions':
                handle = config.get('handle', search_value)
                return handle.lstrip('@')

        # TikTok
        elif provider_key == 'tiktok':
            if search_type == 'user':
                handle = config.get('handle', search_value)
                return handle.lstrip('@')
            elif search_type == 'hashtag':
                return search_value.lstrip('#')
            elif search_type == 'keyword':
                return search_value

        # YouTube
        elif provider_key == 'youtube':
            if search_type == 'channel':
                return config.get('channel_id', search_value)
            elif search_type == 'search':
                return search_value
            elif search_type == 'video':
                return search_value

        # Google News (RSS)
        elif provider_key == 'google_news':
            if search_type == 'rss_keyword':
                # Google News RSS URL format
                from urllib.parse import quote
                return f"https://news.google.com/rss/search?q={quote(search_value)}"

        # Google Search
        elif provider_key == 'google_search':
            if search_type == 'keyword':
                return search_value

        # Default: return the search value as-is
        return search_value

    def _build_feed_label(
        self,
        brand_name: str,
        provider_key: str,
        search_type: str,
        search_value: str
    ) -> str:
        """Build a human-readable label for the feed."""
        provider_display = provider_key.replace('_', ' ').title()
        type_display = search_type.replace('_', ' ').title()

        # Clean up search value for display
        display_value = search_value
        if search_type == 'hashtag':
            display_value = f"#{search_value.lstrip('#')}"
        elif search_type in ('profile', 'user', 'mentions'):
            display_value = f"@{search_value.lstrip('@')}"

        return f"[{brand_name}] {provider_display} - {type_display}: {display_value}"

    def _delete_auto_generated_feeds(self, brand_id: UUID) -> int:
        """
        Delete all auto-generated feeds for a brand.

        Args:
            brand_id: Brand UUID

        Returns:
            Number of feeds deleted
        """
        feeds = self.db.query(FeedConfig).filter(
            FeedConfig.brand_id == brand_id,
            FeedConfig.is_auto_generated == True
        ).all()

        count = len(feeds)
        for feed in feeds:
            self.db.delete(feed)

        if count > 0:
            self.db.commit()
            logger.info(f"Deleted {count} auto-generated feeds for brand {brand_id}")

        return count

    def regenerate_feeds_for_brand(self, brand: BrandConfig) -> List[FeedConfig]:
        """
        Regenerate all feeds for a brand.

        Deletes existing auto-generated feeds and creates new ones.

        Args:
            brand: Brand configuration

        Returns:
            List of newly created FeedConfig objects
        """
        return self.generate_feeds_for_brand(brand, replace_existing=True)

    def get_brand_feeds(
        self,
        brand_id: UUID,
        auto_generated_only: bool = False
    ) -> List[FeedConfig]:
        """
        Get all feeds associated with a brand.

        Args:
            brand_id: Brand UUID
            auto_generated_only: If True, only return auto-generated feeds

        Returns:
            List of FeedConfig objects
        """
        query = self.db.query(FeedConfig).filter(FeedConfig.brand_id == brand_id)

        if auto_generated_only:
            query = query.filter(FeedConfig.is_auto_generated == True)

        return query.all()

    def count_brand_feeds(self, brand_id: UUID) -> Dict[str, int]:
        """
        Count feeds by provider for a brand.

        Args:
            brand_id: Brand UUID

        Returns:
            Dict of provider -> count
        """
        from sqlalchemy import func

        results = self.db.query(
            FeedConfig.provider,
            func.count(FeedConfig.id)
        ).filter(
            FeedConfig.brand_id == brand_id
        ).group_by(
            FeedConfig.provider
        ).all()

        return {provider: count for provider, count in results}

    def validate_social_profiles(
        self,
        social_profiles: Dict[str, Any]
    ) -> List[str]:
        """
        Validate social profiles configuration.

        Args:
            social_profiles: Social profiles dict to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Valid search types per provider
        valid_types = {
            'instagram': {'profile', 'hashtag', 'mentions'},
            'tiktok': {'user', 'hashtag', 'keyword'},
            'youtube': {'channel', 'search', 'video'},
            'google_news': {'rss_keyword'},
            'google_search': {'keyword'},
        }

        for provider_key, config in social_profiles.items():
            if not config:
                continue

            if provider_key not in valid_types:
                errors.append(f"Unknown provider: {provider_key}")
                continue

            if not config.get('enabled'):
                continue

            # Check handle requirement for social media providers
            if provider_key in ('instagram', 'tiktok'):
                searches = config.get('searches', [])
                needs_handle = any(
                    s.get('type') in ('profile', 'user', 'mentions')
                    for s in searches
                )
                if needs_handle and not config.get('handle'):
                    errors.append(f"{provider_key.title()} requires a handle for profile/user searches")

            # Check channel requirement for YouTube
            if provider_key == 'youtube':
                searches = config.get('searches', [])
                needs_channel = any(
                    s.get('type') == 'channel'
                    for s in searches
                )
                if needs_channel and not config.get('channel_id'):
                    errors.append("YouTube requires a channel_id for channel searches")

            # Validate search types
            allowed_types = valid_types[provider_key]
            for search in config.get('searches', []):
                search_type = search.get('type')
                if search_type and search_type not in allowed_types:
                    errors.append(f"Invalid search type '{search_type}' for {provider_key}")

                # Validate count range
                count = search.get('count', 5)
                if count < 1 or count > 100:
                    errors.append(f"Search count must be 1-100, got {count}")

        return errors
