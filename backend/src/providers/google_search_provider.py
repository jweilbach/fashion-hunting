# providers/google_search_provider.py
"""
Google Custom Search API Provider - fetches search results from Google Custom Search
"""

import logging
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .base_provider import ContentProvider

# Create logger for this module
logger = logging.getLogger(__name__)

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    logger.warning("Google API client not installed. Run: pip install google-api-python-client")
    build = None
    HttpError = Exception


class GoogleSearchProvider(ContentProvider):
    """
    Provider for Google Custom Search API.
    Searches Google for specific queries and returns results as standardized items.

    Setup instructions:
    1. Enable Custom Search API in Google Cloud Console
    2. Create a Custom Search Engine at https://programmablesearchengine.google.com/
    3. Get your API key from Google Cloud Console
    4. Get your Search Engine ID from the Custom Search Engine settings
    5. Set environment variables: GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID

    Free tier: 100 queries/day
    Paid tier: $5 per 1,000 queries (up to 10k queries/day)
    """

    def __init__(
        self,
        search_queries: List[str],
        api_key: Optional[str] = None,
        search_engine_id: Optional[str] = None,
        results_per_query: int = 10,
        date_restrict: Optional[str] = "d7"  # Last 7 days by default
    ):
        """
        Initialize Google Search provider.

        Args:
            search_queries: List of search queries to execute (e.g., ["Versace news", "Refinery29 news"])
            api_key: Google API key (falls back to GOOGLE_API_KEY env var)
            search_engine_id: Custom Search Engine ID (falls back to GOOGLE_SEARCH_ENGINE_ID env var)
            results_per_query: Number of results to fetch per query (max 10 per request)
            date_restrict: Time period to restrict results (e.g., 'd7' for last 7 days, 'm1' for last month)
        """
        self.search_queries = search_queries
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.search_engine_id = search_engine_id or os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        self.results_per_query = min(results_per_query, 10)  # API limit is 10 per request
        self.date_restrict = date_restrict

        if not self.api_key:
            raise ValueError("Google API key not provided. Set GOOGLE_API_KEY environment variable.")

        if not self.search_engine_id:
            raise ValueError("Google Search Engine ID not provided. Set GOOGLE_SEARCH_ENGINE_ID environment variable.")

        if build is None:
            raise ImportError("Google API client not installed. Run: pip install google-api-python-client")

        logger.info(f"GoogleSearchProvider initialized with {len(search_queries)} queries")

    def fetch_items(self) -> List[Dict]:
        """
        Fetch items from Google Custom Search API.

        Returns:
            List of standardized item dicts
        """
        items = []

        try:
            # Build the Custom Search service
            service = build("customsearch", "v1", developerKey=self.api_key)

            for query in self.search_queries:
                logger.info(f"Executing Google search: {query}")

                try:
                    # Execute the search request
                    request_params = {
                        'q': query,
                        'cx': self.search_engine_id,
                        'num': self.results_per_query,
                    }

                    # Add date restriction if specified
                    if self.date_restrict:
                        request_params['dateRestrict'] = self.date_restrict

                    result = service.cse().list(**request_params).execute()

                    # Parse results
                    search_items = result.get('items', [])

                    for search_result in search_items:
                        # Extract fields from search result
                        title = search_result.get('title', '').strip()
                        link = search_result.get('link', '').strip()
                        snippet = search_result.get('snippet', '').strip()

                        # Try to extract source/publisher from display link or meta tags
                        source = search_result.get('displayLink', 'Google Search')

                        # Try to get publication date from page metadata
                        pub_date = None
                        page_map = search_result.get('pagemap', {})
                        metatags = page_map.get('metatags', [])
                        if metatags:
                            # Look for common date fields in meta tags
                            meta = metatags[0]
                            for date_field in ['article:published_time', 'publishdate', 'date', 'pubdate']:
                                if date_field in meta:
                                    pub_date = meta[date_field]
                                    break

                        # Create standardized item
                        item = {
                            "source": source,
                            "title": title,
                            "link": link,
                            "raw_summary": snippet,
                            "provider": "GOOGLE_SEARCH",
                            "search_query": query,  # Track which query found this
                        }

                        # Add publication date if found
                        if pub_date:
                            item["published_date"] = pub_date

                        items.append(item)

                    logger.info(f"Fetched {len(search_items)} results for query: {query}")

                except HttpError as e:
                    logger.error(f"HTTP error executing search '{query}': {e}")
                    if e.resp.status == 429:
                        logger.error("Rate limit exceeded. You may have exceeded your daily quota.")
                    continue
                except Exception as e:
                    logger.exception(f"Failed executing search '{query}': {e}")
                    continue

        except Exception as e:
            logger.exception(f"Failed to initialize Google Custom Search service: {e}")
            return []

        logger.info(f"GoogleSearchProvider: Fetched {len(items)} total items from {len(self.search_queries)} queries")
        return items

    def get_provider_name(self) -> str:
        return "GOOGLE_SEARCH"

    # ==========================================
    # Brand 360 Extended Interface Methods
    # ==========================================

    @classmethod
    def get_display_name(cls) -> str:
        return "Google Search"

    @classmethod
    def get_search_types(cls) -> List[Dict]:
        return [
            {'value': 'keyword', 'label': 'Keyword'},
        ]

    @classmethod
    def requires_handle(cls) -> bool:
        return False

    @classmethod
    def is_social_media(cls) -> bool:
        return False

    @classmethod
    def get_provider_type_value(cls) -> str:
        return "GOOGLE_SEARCH"

    @staticmethod
    def generate_brand_queries(brand_names: List[str], query_template: str = "{brand} news") -> List[str]:
        """
        Helper method to generate search queries for a list of brands.

        Args:
            brand_names: List of brand names to search for
            query_template: Template for the query, use {brand} as placeholder

        Returns:
            List of search queries

        Example:
            >>> GoogleSearchProvider.generate_brand_queries(["Versace", "Gucci"], "{brand} latest news")
            ['Versace latest news', 'Gucci latest news']
        """
        return [query_template.format(brand=brand) for brand in brand_names]
