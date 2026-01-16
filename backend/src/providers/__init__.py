"""
Providers package for content fetching.
Contains implementations for different content sources (RSS, TikTok, etc.)
"""

from providers.base_provider import ContentProvider
from providers.registry import ProviderRegistry
from providers.rss_provider import RSSProvider
from providers.google_search_provider import GoogleSearchProvider

# TikTok provider is optional
try:
    from providers.tiktok_provider import TikTokProvider
except ImportError:
    TikTokProvider = None

# Instagram provider is optional
try:
    from providers.instagram_provider import InstagramProvider
except ImportError:
    InstagramProvider = None

# YouTube provider is optional
try:
    from providers.youtube_provider import YouTubeProvider
except ImportError:
    YouTubeProvider = None


# Register all providers with the registry
def _register_providers():
    """Register all available providers with the ProviderRegistry"""
    # Register RSS (Google News)
    ProviderRegistry.register_provider("RSS", RSSProvider)

    # Register Google Search
    ProviderRegistry.register_provider("GOOGLE_SEARCH", GoogleSearchProvider)

    # Register social media providers if available
    if InstagramProvider:
        ProviderRegistry.register_provider("INSTAGRAM", InstagramProvider)

    if TikTokProvider:
        ProviderRegistry.register_provider("TIKTOK", TikTokProvider)

    if YouTubeProvider:
        ProviderRegistry.register_provider("YOUTUBE", YouTubeProvider)


# Auto-register providers on module import
_register_providers()


__all__ = [
    'ContentProvider',
    'ProviderRegistry',
    'RSSProvider',
    'GoogleSearchProvider',
    'TikTokProvider',
    'InstagramProvider',
    'YouTubeProvider',
]
