"""
Providers package for content fetching.
Contains implementations for different content sources (RSS, TikTok, etc.)
"""

from providers.base_provider import ContentProvider
from providers.rss_provider import RSSProvider

# TikTok provider is optional
try:
    from providers.tiktok_provider import TikTokProvider
    __all__ = ['ContentProvider', 'RSSProvider', 'TikTokProvider']
except ImportError:
    __all__ = ['ContentProvider', 'RSSProvider']
