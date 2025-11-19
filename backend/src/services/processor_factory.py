"""
Processor factory - creates the appropriate processor for each provider type
"""
import logging
from typing import Dict

from ai_client import AIClient
from services.base_processor import BaseContentProcessor
from services.article_processor import ArticleProcessor
from services.social_media_processor import SocialMediaProcessor

logger = logging.getLogger(__name__)


class ProcessorFactory:
    """
    Factory for creating content processors based on provider type.

    Maps providers to the appropriate processor:
    - RSS, GOOGLE_SEARCH → ArticleProcessor (web articles)
    - TIKTOK, INSTAGRAM → SocialMediaProcessor (social posts)
    """

    # Mapping of providers to processor classes
    _PROCESSOR_MAP = {
        'RSS': ArticleProcessor,
        'GOOGLE_SEARCH': ArticleProcessor,  # Google Search returns web articles
        'TIKTOK': SocialMediaProcessor,
        'INSTAGRAM': SocialMediaProcessor,
    }

    @classmethod
    def create_processor(
        cls,
        provider: str,
        ai_client: AIClient,
        brands: list = None,
        config: Dict = None
    ) -> BaseContentProcessor:
        """
        Create the appropriate processor for a given provider

        Args:
            provider: Provider name (e.g., 'RSS', 'TIKTOK', 'GOOGLE_SEARCH')
            ai_client: AIClient instance
            brands: List of brands to track
            config: Configuration dict for the processor

        Returns:
            Instance of appropriate processor (ArticleProcessor or SocialMediaProcessor)

        Raises:
            ValueError: If provider is not supported
        """
        provider_upper = provider.upper()

        # Get the processor class for this provider
        processor_class = cls._PROCESSOR_MAP.get(provider_upper)

        if not processor_class:
            supported = ', '.join(cls._PROCESSOR_MAP.keys())
            raise ValueError(
                f"Unsupported provider: {provider}. "
                f"Supported providers: {supported}"
            )

        logger.info(f"Creating {processor_class.__name__} for provider: {provider}")

        # Instantiate and return the processor
        return processor_class(
            ai_client=ai_client,
            brands=brands,
            config=config or {}
        )

    @classmethod
    def get_supported_providers(cls) -> list:
        """
        Get list of all supported providers

        Returns:
            List of provider names
        """
        return list(cls._PROCESSOR_MAP.keys())

    @classmethod
    def get_processor_for_providers(
        cls,
        providers: list,
        ai_client: AIClient,
        brands: list = None,
        config: Dict = None
    ) -> Dict[str, BaseContentProcessor]:
        """
        Create processors for multiple providers

        Args:
            providers: List of provider names
            ai_client: AIClient instance
            brands: List of brands to track
            config: Configuration dict for the processors

        Returns:
            Dict mapping provider names to processor instances
        """
        processors = {}

        for provider in providers:
            try:
                processors[provider] = cls.create_processor(
                    provider=provider,
                    ai_client=ai_client,
                    brands=brands,
                    config=config
                )
            except ValueError as e:
                logger.warning(f"Skipping provider {provider}: {e}")
                continue

        return processors
