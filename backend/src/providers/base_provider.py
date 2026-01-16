# providers/base_provider.py
"""
Base provider interface for content sources.
Each provider (RSS, TikTok, etc.) implements this interface.
"""

from typing import List, Dict, Optional, Set, Tuple
from abc import ABC, abstractmethod


class ContentProvider(ABC):
    """
    Abstract base class for content providers.
    Each provider fetches content items from their respective source.
    """

    @abstractmethod
    def fetch_items(self) -> List[Dict]:
        """
        Fetch content items from the provider.

        Returns:
            List of item dicts with standardized keys:
            - source: str - Source name (e.g., "RSS", "TikTok (@username)")
            - title: str - Item title/description
            - link: str - URL to the content
            - raw_summary: str - Summary/description text
            - additional keys specific to the provider (optional)
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of this provider (e.g., 'RSS', 'TikTok')"""
        pass

    # ==========================================
    # Brand 360 Extended Interface Methods
    # ==========================================

    @classmethod
    def get_display_name(cls) -> str:
        """
        Human-readable name for UI display.
        Override this in subclasses for custom display names.
        """
        # Default implementation - can be overridden
        return cls.__name__.replace("Provider", "").replace("_", " ")

    @classmethod
    def get_search_types(cls) -> List[Dict]:
        """
        Return valid search types for this provider.
        Each provider overrides this to define its search capabilities.

        Returns:
            List of dicts with 'value' and 'label' keys
            Example: [{'value': 'hashtag', 'label': 'Hashtag'}]
        """
        return []

    @classmethod
    def get_search_type_values(cls) -> Set[str]:
        """Get just the valid search type values for validation"""
        return {st['value'] for st in cls.get_search_types()}

    @classmethod
    def requires_handle(cls) -> bool:
        """Whether this provider needs a handle/username to be configured"""
        return False

    @classmethod
    def get_handle_placeholder(cls) -> str:
        """Placeholder text for handle input field"""
        return "@username"

    @classmethod
    def get_handle_label(cls) -> str:
        """Label for handle input field"""
        return "Username"

    @classmethod
    def get_icon_name(cls) -> str:
        """Icon identifier for frontend (lowercase provider name)"""
        name = cls.__name__.replace("Provider", "")
        return name.lower()

    @classmethod
    def is_social_media(cls) -> bool:
        """Whether this is a social media provider (vs news/article source)"""
        return False

    @classmethod
    def validate_handle(cls, handle: str) -> Tuple[bool, Optional[str]]:
        """
        Validate handle format.

        Returns:
            Tuple of (is_valid, error_message)
            error_message is None if valid
        """
        if cls.requires_handle() and not handle:
            return False, f"{cls.get_display_name()} requires a handle"
        return True, None

    @classmethod
    def get_metadata(cls) -> Dict:
        """
        Return full metadata for this provider.
        Used by frontend to render provider cards.
        """
        return {
            'name': cls.get_provider_type_value(),
            'display_name': cls.get_display_name(),
            'search_types': cls.get_search_types(),
            'requires_handle': cls.requires_handle(),
            'handle_placeholder': cls.get_handle_placeholder(),
            'handle_label': cls.get_handle_label(),
            'icon': cls.get_icon_name(),
            'is_social_media': cls.is_social_media(),
        }

    @classmethod
    def get_provider_type_value(cls) -> str:
        """
        Get the provider type value used in database/API.
        Override this if the class name doesn't match the ProviderType enum.
        """
        # Default: uppercase name without "Provider" suffix
        name = cls.__name__.replace("Provider", "").upper()
        return name
