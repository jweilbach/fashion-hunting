"""
Celery tasks for fetching content from feeds
"""
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import feedparser
import hashlib
from uuid import UUID

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from celery_app.celery import app
from models.base import SessionLocal
from repositories.feed_repository import FeedRepository
from repositories.report_repository import ReportRepository
from services.apify_scraper_service import ApifyScraperService
import logging

logger = logging.getLogger(__name__)


@app.task(name='celery_app.tasks.feed_tasks.fetch_rss_feed')
def fetch_rss_feed(feed_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Fetch entries from an RSS feed and create report records
    
    Args:
        feed_id: UUID of the feed configuration
        tenant_id: UUID of the tenant
        
    Returns:
        Dict with fetch results (success count, error count, etc.)
    """
    db = SessionLocal()
    results = {
        'feed_id': feed_id,
        'tenant_id': tenant_id,
        'fetched': 0,
        'created': 0,
        'duplicates': 0,
        'errors': 0,
        'error_messages': []
    }
    
    try:
        feed_repo = FeedRepository(db)
        report_repo = ReportRepository(db)
        
        # Get feed configuration
        feed = feed_repo.get_by_id(UUID(feed_id))
        if not feed or not feed.enabled:
            results['error_messages'].append('Feed not found or disabled')
            return results
        
        # Fetch RSS feed
        parsed_feed = feedparser.parse(feed.feed_value)
        results['fetched'] = len(parsed_feed.entries)
        
        # Process each entry
        for entry in parsed_feed.entries[:feed.fetch_count]:
            try:
                # Extract data from entry
                title = entry.get('title', '')
                link = entry.get('link', '')
                summary = entry.get('summary', entry.get('description', ''))
                
                # Parse timestamp
                published = entry.get('published_parsed') or entry.get('updated_parsed')
                if published:
                    timestamp = datetime(*published[:6])
                else:
                    timestamp = datetime.now()
                
                # Generate dedupe key
                dedupe_content = f"{link}|{title}"
                dedupe_key = hashlib.sha256(dedupe_content.encode()).hexdigest()
                
                # Check for duplicates
                if report_repo.exists_by_dedupe_key(UUID(tenant_id), dedupe_key):
                    results['duplicates'] += 1
                    continue
                
                # Create report (will be processed by another task)
                report = report_repo.create(
                    tenant_id=UUID(tenant_id),
                    source=parsed_feed.feed.get('title', feed.label or 'RSS Feed'),
                    provider='RSS',
                    title=title,
                    link=link,
                    summary=summary,
                    timestamp=timestamp,
                    processing_status='pending',
                    dedupe_key=dedupe_key
                )
                
                results['created'] += 1
                
                # Queue processing task
                from celery_app.tasks.processing_tasks import process_report
                process_report.delay(str(report.id), str(tenant_id))
                
            except Exception as e:
                results['errors'] += 1
                results['error_messages'].append(f"Entry error: {str(e)}")
        
        # Update feed stats
        feed_repo.mark_fetched(UUID(feed_id), success=True)
        
    except Exception as e:
        results['errors'] += 1
        results['error_messages'].append(f"Feed fetch error: {str(e)}")
        
        # Mark feed as failed
        try:
            feed_repo.mark_fetched(UUID(feed_id), success=False, error=str(e))
        except:
            pass
    
    finally:
        db.close()
    
    return results


@app.task(name='celery_app.tasks.feed_tasks.fetch_feed_batch')
def fetch_feed_batch(feed_ids: List[str], tenant_id: str) -> Dict[str, Any]:
    """
    Fetch multiple feeds in batch
    
    Args:
        feed_ids: List of feed UUIDs
        tenant_id: UUID of the tenant
        
    Returns:
        Summary of batch fetch results
    """
    results = {
        'total_feeds': len(feed_ids),
        'successful': 0,
        'failed': 0,
        'total_fetched': 0,
        'total_created': 0
    }
    
    for feed_id in feed_ids:
        try:
            result = fetch_rss_feed.delay(feed_id, tenant_id).get(timeout=300)
            if result['errors'] == 0:
                results['successful'] += 1
            else:
                results['failed'] += 1
            results['total_fetched'] += result['fetched']
            results['total_created'] += result['created']
        except Exception as e:
            results['failed'] += 1
    
    return results
