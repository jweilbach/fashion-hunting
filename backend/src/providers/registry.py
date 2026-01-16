# providers/registry.py
"""
Provider Registry - Central registration and discovery of content providers.
Single source of truth for all provider metadata.
"""

from typing import Dict, List, Optional, Type
from .base_provider import ContentProvider


class ProviderRegistry:
    """
    Central registry for content providers.

    Usage:
        # Register a provider class
        @ProviderRegistry.register
        class InstagramProvider(ContentProvider):
            ...

        # Get all registered providers
        providers = ProviderRegistry.get_all()

        # Get a specific provider
        instagram = ProviderRegistry.get('INSTAGRAM')

        # Get metadata for frontend
        metadata = ProviderRegistry.get_all_metadata()
    """

    _providers: Dict[str, Type[ContentProvider]] = {}

    @classmethod
    def register(cls, provider_class: Type[ContentProvider]) -> Type[ContentProvider]:
        """
        Decorator to register a provider class.

        Usage:
            @ProviderRegistry.register
            class MyProvider(ContentProvider):
                ...
        """
        provider_name = provider_class.get_provider_type_value()
        cls._providers[provider_name] = provider_class
        return provider_class

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[ContentProvider]) -> None:
        """
        Manually register a provider with a specific name.
        Useful for providers where the class name doesn't match the desired key.
        """
        cls._providers[name] = provider_class

    @classmethod
    def get_all(cls) -> Dict[str, Type[ContentProvider]]:
        """Get all registered provider classes"""
        return cls._providers.copy()

    @classmethod
    def get(cls, name: str) -> Optional[Type[ContentProvider]]:
        """Get a provider class by name (case-insensitive)"""
        return cls._providers.get(name.upper())

    @classmethod
    def get_metadata(cls, name: str) -> Optional[Dict]:
        """Get metadata for a specific provider"""
        provider = cls.get(name)
        if provider:
            return provider.get_metadata()
        return None

    @classmethod
    def get_all_metadata(cls) -> List[Dict]:
        """
        Return metadata for all registered providers.
        Used by frontend to render provider cards.
        """
        return [
            provider_class.get_metadata()
            for provider_class in cls._providers.values()
        ]

    @classmethod
    def get_search_types(cls, name: str) -> List[Dict]:
        """Get search types for a specific provider"""
        provider = cls.get(name)
        if provider:
            return provider.get_search_types()
        return []

    @classmethod
    def get_all_search_types(cls) -> Dict[str, List[Dict]]:
        """
        Get search types for all providers.
        Returns: {'INSTAGRAM': [...], 'TIKTOK': [...], ...}
        """
        return {
            name: provider_class.get_search_types()
            for name, provider_class in cls._providers.items()
        }

    @classmethod
    def validate_search_type(cls, provider_name: str, search_type: str) -> bool:
        """Validate that a search type is valid for the given provider"""
        provider = cls.get(provider_name)
        if not provider:
            return False
        return search_type in provider.get_search_type_values()

    @classmethod
    def get_social_media_providers(cls) -> List[str]:
        """Get list of social media provider names"""
        return [
            name for name, provider_class in cls._providers.items()
            if provider_class.is_social_media()
        ]

    @classmethod
    def get_article_providers(cls) -> List[str]:
        """Get list of article/news source provider names"""
        return [
            name for name, provider_class in cls._providers.items()
            if not provider_class.is_social_media()
        ]

    @classmethod
    def clear(cls) -> None:
        """Clear all registered providers (useful for testing)"""
        cls._providers.clear()
