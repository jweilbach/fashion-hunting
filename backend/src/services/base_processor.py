"""
Base content processor - abstract interface for processing different content types
"""
import logging
import hashlib
from typing import Dict, List, Tuple
from abc import ABC, abstractmethod

from ai_client import AIClient

logger = logging.getLogger(__name__)


class BaseContentProcessor(ABC):
    """
    Abstract base class for content processors.
    Different content types (articles, social media posts, videos) require different processing.
    """

    def __init__(
        self,
        ai_client: AIClient,
        brands: List[str] = None,
        config: Dict = None
    ):
        """
        Initialize content processor

        Args:
            ai_client: AIClient instance for content analysis
            brands: List of known brands to track
            config: Additional configuration options
        """
        self.ai_client = ai_client
        self.brands = brands or []
        self.config = config or {}

    @abstractmethod
    def process_item(self, item: Dict) -> Tuple[Dict, str]:
        """
        Process a single content item from a provider

        Args:
            item: Content item dict from provider (format varies by provider)

        Returns:
            Tuple of (processed_data dict, dedupe_key str)
            processed_data contains:
                - full_text: str - Full content text
                - brands: List[str] - Extracted brand mentions
                - summary: str - AI-generated summary
                - sentiment: str - Sentiment analysis result
                - topic: str - Classified topic
                - est_reach: int - Estimated reach
                - provider: str - Provider name
                - source: str - Source name
                - title: str - Content title
                - link: str - Content URL
                - metadata: Dict - Additional provider-specific data
        """
        pass

    def generate_dedupe_key(self, title: str, link: str) -> str:
        """
        Generate deduplication key from title and link

        Args:
            title: Content title
            link: Content URL

        Returns:
            SHA256 hash of title+link
        """
        dedupe_content = f"{title}{link}"
        return hashlib.sha256(dedupe_content.encode()).hexdigest()

    @abstractmethod
    def get_supported_providers(self) -> List[str]:
        """
        Return list of provider names this processor supports

        Returns:
            List of provider names (e.g., ['RSS', 'GOOGLE_SEARCH'])
        """
        pass
