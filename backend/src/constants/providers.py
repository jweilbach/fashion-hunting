"""
Provider type constants and enums for standardized provider identification across the application.

This module defines the canonical source of truth for provider names to ensure consistency
across providers, processors, database records, and API responses.
"""
from enum import Enum


class ProviderType(str, Enum):
    """
    Standard provider type identifiers.

    These values should be used consistently across:
    - Database storage (feed_configs.provider, reports.provider)
    - Provider class get_provider_name() methods
    - ProcessorFactory mapping
    - API responses
    - Frontend display

    Usage:
        provider = ProviderType.INSTAGRAM
        if provider == ProviderType.INSTAGRAM:
            ...

        # String comparison works due to str inheritance
        if some_string == ProviderType.INSTAGRAM:
            ...
    """

    # News/Article sources
    RSS = "RSS"
    GOOGLE_SEARCH = "GOOGLE_SEARCH"

    # Social Media platforms
    INSTAGRAM = "INSTAGRAM"
    TIKTOK = "TIKTOK"
    YOUTUBE = "YOUTUBE"

    @classmethod
    def is_social_media(cls, provider: str) -> bool:
        """Check if provider is a social media platform (no AI processing needed)"""
        social_platforms = {cls.INSTAGRAM, cls.TIKTOK, cls.YOUTUBE}
        return provider in social_platforms or provider in [p.value for p in social_platforms]

    @classmethod
    def is_article_source(cls, provider: str) -> bool:
        """Check if provider is an article/news source (AI processing needed)"""
        article_sources = {cls.RSS, cls.GOOGLE_SEARCH}
        return provider in article_sources or provider in [p.value for p in article_sources]

    @classmethod
    def get_display_name(cls, provider: str) -> str:
        """Get human-friendly display name for provider"""
        display_names = {
            cls.RSS: "RSS Feed",
            cls.GOOGLE_SEARCH: "Google Search",
            cls.INSTAGRAM: "Instagram",
            cls.TIKTOK: "TikTok",
            cls.YOUTUBE: "YouTube",
        }
        return display_names.get(provider, provider)

    @classmethod
    def all_values(cls) -> list:
        """Get list of all provider type values"""
        return [p.value for p in cls]


class FeedType(str, Enum):
    """
    Feed type identifiers for different search/fetch methods.

    Different providers support different feed types:
    - RSS: rss_url
    - GOOGLE_SEARCH: keyword_search, brand_search
    - INSTAGRAM: hashtag, user, location
    - TIKTOK: hashtag, keyword, user
    - YOUTUBE: search, channel, video
    """

    # RSS feed types
    RSS_URL = "rss_url"

    # Google Search feed types
    KEYWORD_SEARCH = "keyword_search"
    BRAND_SEARCH = "brand_search"

    # Instagram feed types
    HASHTAG = "hashtag"
    USER = "user"
    LOCATION = "location"

    # TikTok feed types (uses same as Instagram plus keyword)
    KEYWORD = "keyword"

    # YouTube feed types
    SEARCH = "search"
    CHANNEL = "channel"
    VIDEO = "video"
