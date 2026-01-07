"""
Brand Matcher Utility - Shared brand matching logic for all processors

This module provides a centralized, consistent approach to brand detection across
different content types (hashtags, mentions, text). It eliminates duplicate code
and ensures uniform brand matching behavior across all social media processors.
"""
import re
from typing import List, Set


class BrandMatcher:
    """
    Utility class for matching brand names in various content formats.

    Supports multiple matching strategies:
    - Hashtag matching (start-of-string for social media hashtags)
    - Mention matching (start-of-string for @mentions)
    - Text matching (word boundary regex for titles/descriptions)

    All matching is case-insensitive and handles multi-word brand names.
    """

    def __init__(self, brands: List[str]):
        """
        Initialize the brand matcher with a list of brand names to search for.

        Args:
            brands: List of brand names (e.g., ['Color Wow', 'Versace', 'Nike'])
        """
        self.brands = brands or []

    def match_in_hashtags(self, hashtags: List[str]) -> List[str]:
        """
        Match brand names in hashtags using start-of-string matching.

        This prevents false positives like "#haircolor" matching "color".
        Only matches if the brand name appears at the START of the hashtag.

        Args:
            hashtags: List of hashtags (with or without # prefix)

        Returns:
            List of matched brand names

        Examples:
            >>> matcher = BrandMatcher(['Color Wow', 'Versace'])
            >>> matcher.match_in_hashtags(['#colorwow', '#haircolor', '#versacestyle'])
            ['Color Wow', 'Versace']  # 'haircolor' not matched
        """
        if not self.brands or not hashtags:
            return []

        brands_found: Set[str] = set()

        for hashtag in hashtags:
            # Remove # prefix and normalize
            hashtag_clean = hashtag.lstrip('#').lower().replace(' ', '')

            for brand in self.brands:
                brand_lower = brand.lower().replace(' ', '')

                # Only match if brand appears at START of hashtag
                # This prevents false positives:
                #   ✅ #colorwow → matches "Color Wow"
                #   ✅ #colorwowhair → matches "Color Wow"
                #   ❌ #haircolor → does NOT match "Color Wow"
                if hashtag_clean.startswith(brand_lower):
                    brands_found.add(brand)

        return list(brands_found)

    def match_in_mentions(self, mentions: List[str]) -> List[str]:
        """
        Match brand names in @mentions using start-of-string matching.

        Similar to hashtag matching but for social media @mentions.

        Args:
            mentions: List of mentions (with or without @ prefix)

        Returns:
            List of matched brand names

        Examples:
            >>> matcher = BrandMatcher(['Nike'])
            >>> matcher.match_in_mentions(['@nike', '@nikerunning', '@nikewomen'])
            ['Nike', 'Nike', 'Nike']
        """
        if not self.brands or not mentions:
            return []

        brands_found: Set[str] = set()

        for mention in mentions:
            # Remove @ prefix and normalize
            mention_clean = mention.lstrip('@').lower().replace(' ', '')

            for brand in self.brands:
                brand_lower = brand.lower().replace(' ', '')

                # Only match if brand appears at START of mention
                if mention_clean.startswith(brand_lower):
                    brands_found.add(brand)

        return list(brands_found)

    def match_in_text(self, *texts: str) -> List[str]:
        """
        Match brand names in free-form text using word boundary regex.

        Uses word boundaries (\\b) to avoid partial word matches.
        Useful for titles, descriptions, and other natural language text.

        Args:
            *texts: One or more text strings to search (combined together)

        Returns:
            List of matched brand names

        Examples:
            >>> matcher = BrandMatcher(['Color Wow', 'Versace'])
            >>> matcher.match_in_text('Best Color Wow products', 'Amazing hair care')
            ['Color Wow']
            >>> matcher.match_in_text('Beautiful colorful hair')
            []  # 'colorful' doesn't match 'Color Wow'
        """
        if not self.brands or not any(texts):
            return []

        brands_found: Set[str] = set()

        # Combine all text arguments
        combined_text = ' '.join(text for text in texts if text).lower()

        if not combined_text:
            return []

        for brand in self.brands:
            brand_lower = brand.lower()

            # Use word boundary matching to avoid false positives
            # \\b ensures we match whole words only:
            #   ✅ "Color Wow" → matches "color wow", "Color Wow hair"
            #   ❌ "Color Wow" → does NOT match "colorful", "haircolor"
            #   ✅ "Versace" → matches "Versace", "Versace style"
            pattern = r'\b' + re.escape(brand_lower) + r'\b'

            if re.search(pattern, combined_text):
                brands_found.add(brand)

        return list(brands_found)

    def match_all(
        self,
        hashtags: List[str] = None,
        mentions: List[str] = None,
        texts: List[str] = None
    ) -> List[str]:
        """
        Convenience method to match brands across all content types at once.

        Combines results from hashtags, mentions, and text matching.
        Deduplicates brands found in multiple places.

        Args:
            hashtags: Optional list of hashtags to search
            mentions: Optional list of mentions to search
            texts: Optional list of text strings to search

        Returns:
            Deduplicated list of matched brand names

        Examples:
            >>> matcher = BrandMatcher(['Nike'])
            >>> matcher.match_all(
            ...     hashtags=['#nike', '#running'],
            ...     texts=['Best Nike shoes ever']
            ... )
            ['Nike']
        """
        brands_found: Set[str] = set()

        if hashtags:
            brands_found.update(self.match_in_hashtags(hashtags))

        if mentions:
            brands_found.update(self.match_in_mentions(mentions))

        if texts:
            for text in texts:
                brands_found.update(self.match_in_text(text))

        return list(brands_found)
