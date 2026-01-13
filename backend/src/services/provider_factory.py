"""
Provider Factory - creates the appropriate provider for each feed type

This factory eliminates the need for manual provider handling in job_execution_service.py
by dynamically instantiating providers based on feed configuration.
"""
import logging
from typing import List, Dict, Any

from constants import ProviderType
from providers.base_provider import ContentProvider
from providers.rss_provider import RSSProvider
from providers.google_search_provider import GoogleSearchProvider
from providers.instagram_provider import InstagramProvider
from providers.tiktok_provider import TikTokProvider
from providers.youtube_api_provider import YouTubeAPIProvider  # Using official YouTube Data API v3

logger = logging.getLogger(__name__)


class ProviderFactory:
    """
    Factory for creating content providers based on provider type.

    Centralizes provider instantiation logic to eliminate code duplication.
    """

    # Mapping of provider types to provider classes
    _PROVIDER_MAP = {
        ProviderType.RSS: RSSProvider,
        ProviderType.GOOGLE_SEARCH: GoogleSearchProvider,
        ProviderType.INSTAGRAM: InstagramProvider,
        ProviderType.TIKTOK: TikTokProvider,
        ProviderType.YOUTUBE: YouTubeAPIProvider,  # Using YouTube Data API v3 for full descriptions
    }

    @classmethod
    def create_provider(
        cls,
        provider_type: str,
        feed_configs: List[Dict[str, Any]],
        config: Dict[str, Any] = None
    ) -> ContentProvider:
        """
        Create a provider instance for the given provider type.

        Args:
            provider_type: Provider type (e.g., 'RSS', 'INSTAGRAM', 'TIKTOK')
            feed_configs: List of feed configuration dicts for this provider
            config: Optional configuration dict (used by GoogleSearchProvider)

        Returns:
            Provider instance

        Raises:
            ValueError: If provider type is not supported

        Example:
            >>> feed_configs = [{'type': 'hashtag', 'value': 'fashion', 'count': 30}]
            >>> provider = ProviderFactory.create_provider('TIKTOK', feed_configs)
            >>> items = provider.fetch_items()
        """
        # Normalize provider type to uppercase
        provider_type_normalized = provider_type.upper()

        # Get provider class from mapping
        provider_class = cls._PROVIDER_MAP.get(provider_type_normalized)

        if not provider_class:
            supported = ', '.join(cls._PROVIDER_MAP.keys())
            raise ValueError(
                f"Unsupported provider: {provider_type}. "
                f"Supported providers: {supported}"
            )

        logger.info(f"Creating {provider_class.__name__} for {len(feed_configs)} feeds")

        # Create provider instance based on type
        if provider_type_normalized == ProviderType.RSS:
            # RSS provider takes list of URLs
            urls = [fc.get('value') or fc.get('url') for fc in feed_configs]
            urls = [url for url in urls if url]  # Filter out None values
            return provider_class(urls)

        elif provider_type_normalized == ProviderType.GOOGLE_SEARCH:
            # Google Search provider takes queries and optional config
            queries = [fc.get('value') or fc.get('query') for fc in feed_configs]
            queries = [q for q in queries if q]  # Filter out None values

            # Extract Google-specific config
            results_per_query = config.get('results_per_query', 10) if config else 10
            date_restrict = config.get('date_restrict', 'd7') if config else 'd7'

            return provider_class(
                search_queries=queries,
                results_per_query=results_per_query,
                date_restrict=date_restrict
            )

        elif provider_type_normalized in (ProviderType.INSTAGRAM, ProviderType.TIKTOK, ProviderType.YOUTUBE):
            # Social media providers take list of search configs
            # Feed configs should have 'type' and 'value' keys
            search_configs = []
            for fc in feed_configs:
                search_config = {
                    'type': fc.get('type') or fc.get('feed_type', 'hashtag'),
                    'value': fc.get('value') or fc.get('feed_value', ''),
                    'count': fc.get('count') or fc.get('fetch_count', 30)
                }
                if search_config['value']:  # Only add if value is not empty
                    search_configs.append(search_config)

            return provider_class(search_configs)

        else:
            # Fallback for any other providers (shouldn't reach here)
            raise ValueError(f"No instantiation logic defined for provider: {provider_type}")

    @classmethod
    def get_supported_providers(cls) -> List[str]:
        """Get list of all supported provider types"""
        return list(cls._PROVIDER_MAP.keys())

    @classmethod
    def is_supported(cls, provider_type: str) -> bool:
        """Check if a provider type is supported"""
        return provider_type.upper() in cls._PROVIDER_MAP
