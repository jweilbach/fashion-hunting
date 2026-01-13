"""
Feeds Router
Handles CRUD operations for feed configurations
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from api.database import get_db
from api import schemas
from api.auth import get_current_user, require_viewer, require_editor, require_admin
from models.user import User
from repositories.feed_repository import FeedRepository

router = APIRouter()


@router.get("/", response_model=List[schemas.FeedConfig])
async def list_feeds(
    provider: Optional[str] = Query(None, description="Filter by provider (RSS, TikTok, etc)"),
    enabled_only: Optional[bool] = Query(None, description="Filter enabled feeds only"),
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """
    List all feed configurations for the current user's tenant

    - **provider**: Filter by provider (RSS, TikTok, etc)
    - **enabled_only**: Filter enabled feeds only
    """
    repo = FeedRepository(db)
    feeds = repo.get_all(current_user.tenant_id, provider=provider, enabled_only=enabled_only or False)
    return [schemas.FeedConfig.model_validate(f) for f in feeds]


@router.get("/{feed_id}", response_model=schemas.FeedConfig)
async def get_feed(
    feed_id: UUID,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Get a specific feed configuration by ID"""
    repo = FeedRepository(db)
    feed = repo.get_by_id(feed_id)

    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed not found"
        )

    # Verify tenant access
    if feed.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return schemas.FeedConfig.model_validate(feed)


@router.post("/", response_model=schemas.FeedConfig, status_code=status.HTTP_201_CREATED)
async def create_feed(
    feed_data: schemas.FeedConfigCreate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Create a new feed configuration (requires editor role)

    - **provider**: Provider type (RSS, TikTok, Instagram)
    - **feed_type**: Feed type (hashtag, keyword, user, rss_url)
    - **feed_value**: The actual URL, hashtag, or username
    - **label**: Optional label for the feed
    - **enabled**: Whether the feed is enabled
    - **fetch_count**: Number of items to fetch
    - **config**: Additional feed configuration
    """
    repo = FeedRepository(db)

    # Prepare config - convert feed_type to search_type for Instagram
    config = feed_data.config or {}
    if feed_data.provider.upper() == 'INSTAGRAM' and not config.get('search_type'):
        # Map feed_type to search_type for Instagram
        feed_type_mapping = {
            'user': 'profile',     # UI uses 'user', backend uses 'profile'
            'hashtag': 'hashtag',
            'keyword': 'mentions',  # keyword searches use hashtag mentions
        }
        search_type = feed_type_mapping.get(feed_data.feed_type, 'mentions')
        config['search_type'] = search_type

    # Create feed
    feed = repo.create(
        tenant_id=current_user.tenant_id,
        provider=feed_data.provider,
        feed_type=feed_data.feed_type,
        feed_value=feed_data.feed_value,
        label=feed_data.label,
        enabled=feed_data.enabled,
        fetch_count=feed_data.fetch_count,
        config=config
    )

    return schemas.FeedConfig.model_validate(feed)


@router.patch("/{feed_id}", response_model=schemas.FeedConfig)
@router.put("/{feed_id}", response_model=schemas.FeedConfig)
async def update_feed(
    feed_id: UUID,
    feed_update: schemas.FeedConfigUpdate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """Update a feed configuration (requires editor role)"""
    repo = FeedRepository(db)
    feed = repo.get_by_id(feed_id)

    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed not found"
        )

    # Verify tenant access
    if feed.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Update fields
    update_data = feed_update.model_dump(exclude_unset=True)
    updated_feed = repo.update(feed_id, **update_data)

    return schemas.FeedConfig.model_validate(updated_feed)


@router.delete("/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feed(
    feed_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete a feed configuration (requires admin role)"""
    repo = FeedRepository(db)
    feed = repo.get_by_id(feed_id)

    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed not found"
        )

    # Verify tenant access
    if feed.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    repo.delete(feed_id)
    return None
