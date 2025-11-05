# providers/base_provider.py
"""
Base provider interface for content sources.
Each provider (RSS, TikTok, etc.) implements this interface.
"""

from typing import List, Dict, Optional
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