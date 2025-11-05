# providers/rss_provider.py
"""
RSS Feed Provider - wraps existing RSS feed fetching logic
"""

import logging
import feedparser
import re
from typing import List, Dict
from html import unescape as html_unescape
from .base_provider import ContentProvider


def clean_html_to_text(s: str) -> str:
    """Clean HTML tags from text"""
    if not s:
        return ""
    s = html_unescape(s)
    s = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", s)
    s = re.sub(r"(?s)<.*?>", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


class RSSProvider(ContentProvider):
    """
    Provider for RSS/Atom feeds.
    Maintains the existing RSS feed logic from fetch_and_report.py
    """
    
    def __init__(self, feed_urls: List[str]):
        """
        Initialize RSS provider.
        
        Args:
            feed_urls: List of RSS/Atom feed URLs to fetch
        """
        self.feed_urls = feed_urls
        logging.info(f"RSSProvider initialized with {len(feed_urls)} feeds")
    
    def fetch_items(self) -> List[Dict]:
        """
        Fetch items from all configured RSS feeds.
        
        Returns:
            List of standardized item dicts
        """
        items = []
        
        for url in self.feed_urls:
            logging.info(f"Fetching RSS feed: {url}")
            
            try:
                d = feedparser.parse(url)
                
                for e in d.entries:
                    # Extract source name
                    source = "RSS"
                    try:
                        if hasattr(e, "source") and e.source and hasattr(e.source, "title"):
                            source = e.source.title
                    except Exception:
                        pass
                    
                    # Extract basic fields
                    title = (getattr(e, "title", "") or "").strip()
                    link = (getattr(e, "link", "") or "").strip()
                    raw_summary_html = getattr(e, "summary", "") or ""
                    raw_summary = clean_html_to_text(raw_summary_html)
                    
                    # Create standardized item
                    item = {
                        "source": source,
                        "title": title,
                        "link": link,
                        "raw_summary": raw_summary,
                        "provider": "RSS",
                    }
                    
                    items.append(item)
                    
                logging.info(f"Fetched {len(d.entries)} items from {url}")
                
            except Exception as e:
                logging.exception(f"Failed parsing feed {url}: {e}")
                continue
        
        logging.info(f"RSSProvider: Fetched {len(items)} total items from {len(self.feed_urls)} feeds")
        return items
    
    def get_provider_name(self) -> str:
        return "RSS"