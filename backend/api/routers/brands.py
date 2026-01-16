"""
Brands Router
Handles CRUD operations for brand configurations
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
from models.feed import FeedConfig
from repositories.brand_repository import BrandRepository
from services.brand_feed_generator import BrandFeedGenerator

router = APIRouter()


@router.get("/", response_model=List[schemas.BrandConfig])
async def list_brands(
    known_only: Optional[bool] = Query(None, description="Filter known brands only"),
    category: Optional[str] = Query(None, description="Filter by category (client, competitor, industry)"),
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """
    List all brand configurations for the current user's tenant

    - **known_only**: Filter known brands only (optional)
    - **category**: Filter by category (optional)
    """
    repo = BrandRepository(db)
    brands = repo.get_all(current_user.tenant_id, known_only=known_only or False, category=category)
    return [schemas.BrandConfig.model_validate(b) for b in brands]


@router.get("/{brand_id}", response_model=schemas.BrandConfig)
async def get_brand(
    brand_id: UUID,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Get a specific brand configuration by ID"""
    repo = BrandRepository(db)
    brand = repo.get_by_id(brand_id)

    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )

    # Verify tenant access
    if brand.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return schemas.BrandConfig.model_validate(brand)


@router.get("/name/{brand_name}", response_model=schemas.BrandConfig)
async def get_brand_by_name(
    brand_name: str,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Get a brand configuration by name"""
    repo = BrandRepository(db)
    brand = repo.get_by_name(current_user.tenant_id, brand_name)

    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand '{brand_name}' not found"
        )

    return schemas.BrandConfig.model_validate(brand)


@router.post("/", response_model=schemas.BrandConfig, status_code=status.HTTP_201_CREATED)
async def create_brand(
    brand_data: schemas.BrandConfigCreate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Create a new brand configuration (requires editor role)

    - **brand_name**: Name of the brand
    - **aliases**: Optional list of brand name aliases for matching
    - **is_known_brand**: Whether this is a known/tracked brand
    - **should_ignore**: Whether to ignore this brand in reports
    - **category**: Category (client, competitor, industry)
    - **notes**: Additional notes about the brand
    - **social_profiles**: Social media profile configuration (Brand 360)
    """
    repo = BrandRepository(db)

    # Check if brand already exists
    existing_brand = repo.get_by_name(current_user.tenant_id, brand_data.brand_name)
    if existing_brand:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Brand '{brand_data.brand_name}' already exists"
        )

    # Create brand
    brand = repo.create(
        tenant_id=current_user.tenant_id,
        brand_name=brand_data.brand_name,
        aliases=brand_data.aliases,
        is_known_brand=brand_data.is_known_brand,
        should_ignore=brand_data.should_ignore,
        category=brand_data.category,
        notes=brand_data.notes,
        social_profiles=brand_data.social_profiles.model_dump() if brand_data.social_profiles else {}
    )

    # Auto-generate feeds from social profiles (Brand 360)
    if brand_data.social_profiles:
        feed_generator = BrandFeedGenerator(db)
        feed_generator.generate_feeds_for_brand(brand)

    return schemas.BrandConfig.model_validate(brand)


@router.patch("/{brand_id}", response_model=schemas.BrandConfig)
@router.put("/{brand_id}", response_model=schemas.BrandConfig)
async def update_brand(
    brand_id: UUID,
    brand_update: schemas.BrandConfigUpdate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """Update a brand configuration (requires editor role)"""
    repo = BrandRepository(db)
    brand = repo.get_by_id(brand_id)

    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )

    # Verify tenant access
    if brand.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Update fields
    update_data = brand_update.model_dump(exclude_unset=True)

    # Check if social_profiles is being updated
    social_profiles_changed = 'social_profiles' in update_data and update_data['social_profiles'] is not None

    updated_brand = repo.update(brand_id, **update_data)

    # Regenerate feeds if social_profiles changed
    if social_profiles_changed:
        feed_generator = BrandFeedGenerator(db)
        feed_generator.regenerate_feeds_for_brand(updated_brand)

    return schemas.BrandConfig.model_validate(updated_brand)


@router.get("/{brand_id}/feeds", response_model=List[schemas.FeedConfig])
async def get_brand_feeds(
    brand_id: UUID,
    auto_generated_only: bool = Query(False, description="Only return auto-generated feeds"),
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """
    Get all feeds linked to a brand (Brand 360).

    - **auto_generated_only**: Only return auto-generated feeds
    """
    repo = BrandRepository(db)
    brand = repo.get_by_id(brand_id)

    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )

    # Verify tenant access
    if brand.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Query feeds linked to this brand
    query = db.query(FeedConfig).filter(FeedConfig.brand_id == brand_id)
    if auto_generated_only:
        query = query.filter(FeedConfig.is_auto_generated == True)

    feeds = query.all()
    return [schemas.FeedConfig.model_validate(f) for f in feeds]


@router.post("/{brand_id}/regenerate-feeds", response_model=List[schemas.FeedConfig])
async def regenerate_brand_feeds(
    brand_id: UUID,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Regenerate all auto-generated feeds for a brand (Brand 360).

    Deletes existing auto-generated feeds and creates new ones based on
    the brand's current social_profiles configuration.
    """
    repo = BrandRepository(db)
    brand = repo.get_by_id(brand_id)

    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )

    # Verify tenant access
    if brand.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Regenerate feeds
    feed_generator = BrandFeedGenerator(db)
    feeds = feed_generator.regenerate_feeds_for_brand(brand)

    return [schemas.FeedConfig.model_validate(f) for f in feeds]


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand(
    brand_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete a brand configuration (requires admin role)"""
    repo = BrandRepository(db)
    brand = repo.get_by_id(brand_id)

    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )

    # Verify tenant access
    if brand.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    repo.delete(brand_id)
    return None
