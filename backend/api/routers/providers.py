"""
Providers Router
Provides endpoints for provider metadata and search types (Brand 360)
"""
from fastapi import APIRouter, Depends
from typing import Dict, List
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from api.auth import get_current_user, require_viewer
from models.user import User

# Import provider registry
from providers import ProviderRegistry

router = APIRouter()


@router.get("/search-types", response_model=Dict[str, List[Dict]])
async def get_all_search_types(
    current_user: User = Depends(require_viewer)
):
    """
    Get search types for all registered providers.

    Returns a dictionary mapping provider names to their valid search types.

    Example response:
    ```json
    {
        "INSTAGRAM": [
            {"value": "profile", "label": "Profile"},
            {"value": "hashtag", "label": "Hashtag"},
            {"value": "mentions", "label": "Mentions"}
        ],
        "TIKTOK": [
            {"value": "user", "label": "User"},
            {"value": "hashtag", "label": "Hashtag"},
            {"value": "keyword", "label": "Keyword"}
        ],
        ...
    }
    ```
    """
    return ProviderRegistry.get_all_search_types()


@router.get("/metadata", response_model=List[Dict])
async def get_provider_metadata(
    current_user: User = Depends(require_viewer)
):
    """
    Get full metadata for all registered providers.

    Returns comprehensive information about each provider including:
    - name: Provider identifier
    - display_name: Human-readable name
    - search_types: Valid search types
    - requires_handle: Whether a handle/username is needed
    - handle_placeholder: Placeholder for handle input
    - handle_label: Label for handle input
    - icon: Icon identifier
    - is_social_media: Whether this is a social media provider

    This endpoint is used by the frontend to render provider configuration cards.
    """
    return ProviderRegistry.get_all_metadata()


@router.get("/{provider_name}/search-types", response_model=List[Dict])
async def get_provider_search_types(
    provider_name: str,
    current_user: User = Depends(require_viewer)
):
    """
    Get search types for a specific provider.

    Path Parameters:
    - **provider_name**: Provider identifier (e.g., INSTAGRAM, TIKTOK, YOUTUBE, RSS, GOOGLE_SEARCH)

    Returns a list of valid search types for the specified provider.
    """
    return ProviderRegistry.get_search_types(provider_name.upper())


@router.get("/{provider_name}/metadata", response_model=Dict)
async def get_single_provider_metadata(
    provider_name: str,
    current_user: User = Depends(require_viewer)
):
    """
    Get metadata for a specific provider.

    Path Parameters:
    - **provider_name**: Provider identifier (e.g., INSTAGRAM, TIKTOK, YOUTUBE, RSS, GOOGLE_SEARCH)
    """
    metadata = ProviderRegistry.get_metadata(provider_name.upper())
    if not metadata:
        return {"error": f"Provider '{provider_name}' not found"}
    return metadata
