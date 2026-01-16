# Brand 360 Feature Implementation

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Database migrations | ✅ Complete | All 4 migrations applied |
| Brand `social_profiles` JSONB | ✅ Complete | Model and schema updated |
| Feed `brand_id` + `is_auto_generated` | ✅ Complete | Model and schema updated |
| Job `generate_summary` flag | ✅ Complete | Model and schema updated |
| `summaries` table | ✅ Complete | Migration applied |
| BrandFeedGenerator service | ✅ Complete | Auto-generates feeds from social_profiles |
| Brand creation triggers feed generation | ✅ Complete | Connected in brands.py router |
| Brand update triggers feed regeneration | ✅ Complete | When social_profiles changes |
| Regenerate feeds endpoint | ✅ Complete | POST /brands/{id}/regenerate-feeds |
| Frontend brand feeds API | ✅ Complete | getBrandFeeds, regenerateBrandFeeds |
| Jobs auto-populate feeds from brand | ✅ Complete | Frontend handleBrandChange |
| S3 storage for summaries | ✅ Complete | S3Service with pre-signed URLs |
| AI summary generation (Gemini) | ✅ Complete | Multi-provider AI client |
| PDF generation | ✅ Complete | ReportLab PDF generator |
| Summaries API router | ✅ Complete | CRUD + download endpoints |
| Summaries frontend | 🔄 Pending | SummaryList, Summaries page |
| Dashboard Recent Summaries | 🔄 Pending | Integration pending |

## Reference Files

| File | Description |
|------|-------------|
| `brand_dialog_mockup.html` | HTML mockup of redesigned brand creation dialog with provider cards |
| `dashboard_mockup.html` | HTML mockup of Dashboard with Recent Summaries section |

---

## Overview

When adding a brand, users can optionally provide social media profiles (Instagram, TikTok, YouTube). The system auto-generates comprehensive tracking feeds across all selected platforms. Jobs can optionally generate AI-powered PDF summary documents stored in S3 with pre-signed URL downloads.

---

## Phase 1: Database Schema Changes

### 1.1 Extend `brand_configs` Table

**Migration**: `backend/migrations/add_brand_social_profiles.sql`

```sql
ALTER TABLE brand_configs
ADD COLUMN social_profiles JSONB DEFAULT '{}';

-- Add GIN index for querying inside JSONB
CREATE INDEX idx_brand_configs_social_profiles ON brand_configs USING GIN (social_profiles);
```

**Model Update**: `backend/src/models/brand.py`
```python
social_profiles = Column(JSONB, default=dict)  # Flexible per-provider config
```

**JSONB Structure** - Provider-specific with explicit searches:

```json
{
  "instagram": {
    "enabled": true,
    "handle": "nike",
    "searches": [
      { "type": "profile", "value": "nike", "count": 10 },
      { "type": "hashtag", "value": "nike", "count": 20 },
      { "type": "hashtag", "value": "justdoit", "count": 20 },
      { "type": "mentions", "value": "nike", "count": 10 }
    ]
  },
  "tiktok": {
    "enabled": true,
    "handle": "nike",
    "searches": [
      { "type": "user", "value": "nike", "count": 10 },
      { "type": "hashtag", "value": "nike", "count": 20 },
      { "type": "keyword", "value": "nike shoes", "count": 20 }
    ]
  },
  "youtube": {
    "enabled": true,
    "channel_id": "UCxyz",
    "channel_handle": "@nike",
    "searches": [
      { "type": "channel", "value": "UCxyz", "count": 10 },
      { "type": "search", "value": "nike", "count": 20 },
      { "type": "search", "value": "nike commercial", "count": 10 }
    ]
  },
  "google_news": {
    "enabled": true,
    "searches": [
      { "type": "rss_keyword", "value": "Nike", "count": 30 }
    ]
  },
  "google_search": {
    "enabled": false,
    "searches": [
      { "type": "keyword", "value": "Nike news", "count": 10 }
    ]
  }
}
```

**Valid Search Types per Provider**:

| Provider | Valid Types | Notes |
|----------|-------------|-------|
| Instagram | `profile`, `hashtag`, `mentions` | handle required for profile |
| TikTok | `user`, `hashtag`, `keyword` | handle required for user |
| YouTube | `channel`, `search`, `video` | channel_id for channel type |
| Google News | `rss_keyword` | Free, uses Google News RSS |
| Google Search | `keyword` | Paid API, limited queries |

**Search Entry Structure**:
- `type`: One of the valid types for that provider
- `value`: The search term/handle/hashtag (without # or @)
- `count`: Number of results to fetch (1-100, default 5 from tenant settings)

**Benefits of this approach**:
- Full user control over each search
- Provider-specific validation (only valid types allowed)
- Extensible - add new providers or search types without migrations
- Count per search allows fine-tuning API usage
- Clear mapping to feed generation

### 1.2 Extend `feed_configs` Table

**Migration**: `backend/migrations/add_feed_brand_linkage.sql`

```sql
ALTER TABLE feed_configs
ADD COLUMN brand_id UUID REFERENCES brand_configs(id) ON DELETE SET NULL,
ADD COLUMN is_auto_generated BOOLEAN DEFAULT FALSE;
CREATE INDEX idx_feed_configs_brand_id ON feed_configs(brand_id);
```

**Model Update**: `backend/src/models/feed.py`

**Purpose of `is_auto_generated`:**
- Distinguishes feeds created automatically from brand setup vs manually created by users
- Allows "Regenerate Feeds" on a brand to only replace auto-generated feeds
- Shows "Auto" badge in UI for visibility
- When brand social_profiles change, only auto-generated feeds are updated

### 1.3 New `summaries` Table

**New Model**: `backend/src/models/summary.py`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| tenant_id | UUID | FK to tenants |
| job_id | UUID | FK to scheduled_jobs |
| execution_id | UUID | FK to job_executions |
| brand_ids | UUID[] | Brands included |
| title | VARCHAR(500) | Summary title |
| executive_summary | TEXT | AI-generated text |
| period_start/end | TIMESTAMP | Time range covered |
| file_path | VARCHAR(500) | Local filesystem path (Phase 1) |
| file_size_bytes | INT | File size |
| report_count | INT | Reports summarized |
| generation_status | VARCHAR(50) | pending/generating/completed/failed |

**Storage Strategy:**
- ✅ **Implemented**: S3 storage with pre-signed URLs for secure downloads
- PDFs stored in S3 bucket configured via `AWS_S3_BUCKET` environment variable
- Pre-signed URLs generated with 1-hour expiration for downloads

The `summaries` table includes `s3_bucket` and `s3_key` columns for S3 storage.

### 1.4 Extend `scheduled_jobs` Table

**Migration**: `backend/migrations/add_job_generate_summary.sql`

```sql
ALTER TABLE scheduled_jobs
ADD COLUMN generate_summary BOOLEAN DEFAULT FALSE;
```

**Model Update**: `backend/src/models/job.py`
```python
generate_summary = Column(Boolean, default=False)  # Whether to create AI summary after execution
```

**Behavior**:
- When `generate_summary=True`, after job completes successfully, SummaryService creates a PDF summary
- Summary includes all reports from that job execution
- Toggle visible in Jobs page UI when creating/editing jobs

### 1.5 Tenant Settings (JSONB)

Add to `tenants.settings`:
```json
{
  "brand_360_defaults": {
    "default_schedule_times": ["05:00", "20:00"],
    "timezone": "America/New_York",
    "default_search_count": 5
  }
}
```

---

## Phase 2: Backend Services

### 2.0 Multi-Provider AI Client Refactor (REQUIRED FIRST)

The current `ai_client.py` is tightly coupled to OpenAI. We need a flexible architecture that supports multiple AI providers for different use cases (e.g., OpenAI for brand extraction, Gemini for summaries).

**Files to create/modify:**

#### 2.0.1 Base AI Provider Interface

**File**: `backend/src/ai/base.py`

```python
from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel

class AIResponse(BaseModel):
    """Standard response from any AI provider"""
    content: str
    model: str
    provider: str
    tokens_used: Optional[int] = None

class BaseAIProvider(ABC):
    """Base class for all AI providers"""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider identifier (e.g., 'openai', 'gemini')"""
        pass

    @abstractmethod
    def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1000,
        json_mode: bool = False,
    ) -> AIResponse:
        """
        Send a completion request to the AI provider.

        Args:
            prompt: The prompt to send
            model: Model to use (provider-specific). If None, uses default.
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
            json_mode: If True, request JSON-formatted response

        Returns:
            AIResponse with content and metadata
        """
        pass

    @classmethod
    def get_available_models(cls) -> list[str]:
        """Return list of available models for this provider"""
        return []
```

#### 2.0.2 OpenAI Provider (existing logic extracted)

**File**: `backend/src/ai/providers/openai_provider.py`

```python
import os
import requests
from ..base import BaseAIProvider, AIResponse

class OpenAIProvider(BaseAIProvider):
    """OpenAI API provider"""

    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")

    def get_provider_name(self) -> str:
        return "openai"

    def complete(self, prompt: str, model: Optional[str] = None, ...) -> AIResponse:
        model = model or self.DEFAULT_MODEL
        # ... existing OpenAI API call logic ...

    @classmethod
    def get_available_models(cls) -> list[str]:
        return ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
```

#### 2.0.3 Gemini Provider (NEW)

**File**: `backend/src/ai/providers/gemini_provider.py`

```python
import os
import google.generativeai as genai
from ..base import BaseAIProvider, AIResponse

class GeminiProvider(BaseAIProvider):
    """Google Gemini API provider"""

    DEFAULT_MODEL = "gemini-1.5-flash"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set")
        genai.configure(api_key=self.api_key)

    def get_provider_name(self) -> str:
        return "gemini"

    def complete(self, prompt: str, model: Optional[str] = None, ...) -> AIResponse:
        model_name = model or self.DEFAULT_MODEL
        model = genai.GenerativeModel(model_name)

        generation_config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        if json_mode:
            generation_config.response_mime_type = "application/json"

        response = model.generate_content(prompt, generation_config=generation_config)

        return AIResponse(
            content=response.text,
            model=model_name,
            provider="gemini",
            tokens_used=response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else None
        )

    @classmethod
    def get_available_models(cls) -> list[str]:
        return ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"]
```

#### 2.0.4 AI Client Factory

**File**: `backend/src/ai/factory.py`

```python
from typing import Optional
from .base import BaseAIProvider
from .providers.openai_provider import OpenAIProvider
from .providers.gemini_provider import GeminiProvider

class AIProviderFactory:
    """Factory for creating AI provider instances"""

    _providers = {
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
    }

    @classmethod
    def get_provider(cls, provider_name: str, api_key: Optional[str] = None) -> BaseAIProvider:
        """Get an AI provider instance by name"""
        if provider_name not in cls._providers:
            raise ValueError(f"Unknown AI provider: {provider_name}. Available: {list(cls._providers.keys())}")
        return cls._providers[provider_name](api_key=api_key)

    @classmethod
    def get_available_providers(cls) -> list[str]:
        return list(cls._providers.keys())

    @classmethod
    def register_provider(cls, name: str, provider_class: type[BaseAIProvider]):
        """Register a new AI provider"""
        cls._providers[name] = provider_class
```

#### 2.0.5 Unified AI Client (refactored)

**File**: `backend/src/ai/client.py`

```python
from typing import Optional, List
from .factory import AIProviderFactory
from .base import BaseAIProvider

class AIClient:
    """
    Unified AI client that can use any registered provider.

    Usage:
        # Default (OpenAI)
        client = AIClient()

        # Specific provider
        client = AIClient(provider="gemini")

        # With custom API key
        client = AIClient(provider="openai", api_key="sk-...")
    """

    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        default_model: Optional[str] = None
    ):
        self.provider = AIProviderFactory.get_provider(provider, api_key)
        self.default_model = default_model

    def complete(self, prompt: str, **kwargs) -> str:
        """Simple completion - returns just the content"""
        if self.default_model and "model" not in kwargs:
            kwargs["model"] = self.default_model
        response = self.provider.complete(prompt, **kwargs)
        return response.content

    # ... existing methods refactored to use self.provider.complete() ...
    # classify_summarize, extract_brands_from_*, etc.
```

#### 2.0.6 Configuration

**Add to `.env`:**
```env
# AI Providers
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...

# Default providers for different tasks (optional)
AI_BRAND_EXTRACTION_PROVIDER=openai
AI_BRAND_EXTRACTION_MODEL=gpt-4o-mini
AI_SUMMARY_PROVIDER=gemini
AI_SUMMARY_MODEL=gemini-1.5-flash
```

**Add to `requirements.txt`:**
```
google-generativeai>=0.8.0
```

#### 2.0.7 Usage in SummaryService

```python
# backend/src/services/summary_service.py
from src.ai.client import AIClient

class SummaryService:
    def __init__(self):
        # Use Gemini for summaries (cheaper, good at long-form)
        self.ai_client = AIClient(
            provider=os.getenv("AI_SUMMARY_PROVIDER", "gemini"),
            default_model=os.getenv("AI_SUMMARY_MODEL", "gemini-1.5-flash")
        )

    def generate_executive_summary(self, reports: list[Report]) -> str:
        """Generate AI summary of reports using configured provider"""
        prompt = self._build_summary_prompt(reports)
        return self.ai_client.complete(prompt, max_tokens=2000)
```

**Benefits:**
- Swap providers without code changes (just env vars)
- Different providers for different tasks (OpenAI for extraction, Gemini for summaries)
- Easy to add new providers (Claude, Mistral, local models, etc.)
- Consistent interface across all AI operations
- Cost optimization (use cheaper models where appropriate)

---

### 2.1 Brand Feed Generator Service ✅ IMPLEMENTED

**File**: `backend/src/services/brand_feed_generator.py`

Auto-generates feeds when brand is created or updated. **Connected to brands router** - brand creation with `social_profiles` automatically triggers feed generation.

**Integration points** (in `backend/api/routers/brands.py`):
- `POST /brands/` - Calls `BrandFeedGenerator.generate_feeds_for_brand()` after creation
- `PATCH/PUT /brands/{id}` - Calls `BrandFeedGenerator.regenerate_feeds_for_brand()` when social_profiles change
- `POST /brands/{id}/regenerate-feeds` - Manual regeneration endpoint

**Supported feed types:**
- Instagram hashtag searches
- Instagram profile monitoring (if handle provided)
- TikTok hashtag/keyword searches
- TikTok profile monitoring (if handle provided)
- YouTube searches
- YouTube channel monitoring (if channel provided)
- Google News RSS: `https://news.google.com/rss/search?q={brand}`
- Google Search feed (if enabled)

### 2.2 S3 Storage Service ✅ IMPLEMENTED

**File**: `backend/src/services/s3_service.py`

```python
class S3Service:
    """S3 storage for PDF summaries with pre-signed URL support"""

    def __init__(self):
        self.bucket = os.getenv("AWS_S3_BUCKET")
        self.client = boto3.client('s3', ...)

    def upload_pdf(self, key: str, pdf_bytes: bytes) -> str:
        """Upload PDF to S3, return S3 key"""

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate pre-signed URL for secure download"""

    def delete_file(self, key: str) -> bool:
        """Delete file from S3"""
```

**S3 path structure**: `summaries/{tenant_id}/{summary_id}.pdf`

**Environment variables required:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `AWS_S3_BUCKET`

### 2.3 PDF Generator Service (NEW)

**File**: `backend/src/services/pdf_generator.py`

Uses `reportlab` library. Generates PDF with:
- Title and date range
- Brands covered
- AI executive summary
- Sentiment breakdown table
- Activity by platform
- Top mentions

### 2.4 Summary Service (NEW)

**File**: `backend/src/services/summary_service.py`

Orchestrates summary generation:
1. Create summary record (status=pending)
2. Fetch reports from execution timeframe
3. Generate AI summary via OpenAI
4. Create PDF using PDFGenerator
5. Save PDF to local filesystem via FileStorageService
6. Update record with file path and status=completed

### 2.5 Update Job Execution Service

**File**: `backend/src/services/job_execution_service.py`

After job completion, check `config.generate_summary`. If true, call `SummaryService.generate_summary_for_execution()`.

---

## Phase 3: Backend API Changes

### 3.1 Update Base Provider with Search Types

**File**: `backend/src/providers/base.py`

Add `get_search_types()` method to base provider:

```python
class BaseProvider(ABC):
    # ... existing methods ...

    @classmethod
    def get_search_types(cls) -> list[dict]:
        """
        Return valid search types for this provider.
        Each provider overrides this to define its search capabilities.

        Returns:
            List of dicts with 'value' and 'label' keys
            Example: [{'value': 'hashtag', 'label': 'Hashtag'}]
        """
        return []

    @classmethod
    def get_search_type_values(cls) -> set[str]:
        """Get just the valid search type values for validation"""
        return {st['value'] for st in cls.get_search_types()}
```

**Each provider implements this:**

```python
# instagram_provider.py
@classmethod
def get_search_types(cls) -> list[dict]:
    return [
        {'value': 'profile', 'label': 'Profile'},
        {'value': 'hashtag', 'label': 'Hashtag'},
        {'value': 'mentions', 'label': 'Mentions'},
    ]

# tiktok_provider.py
@classmethod
def get_search_types(cls) -> list[dict]:
    return [
        {'value': 'user', 'label': 'User'},
        {'value': 'hashtag', 'label': 'Hashtag'},
        {'value': 'keyword', 'label': 'Keyword'},
    ]

# youtube_provider.py
@classmethod
def get_search_types(cls) -> list[dict]:
    return [
        {'value': 'channel', 'label': 'Channel'},
        {'value': 'search', 'label': 'Search'},
        {'value': 'video', 'label': 'Video'},
    ]

# rss_provider.py (Google News)
@classmethod
def get_search_types(cls) -> list[dict]:
    return [
        {'value': 'rss_keyword', 'label': 'RSS Keyword'},
    ]

# google_search_provider.py
@classmethod
def get_search_types(cls) -> list[dict]:
    return [
        {'value': 'keyword', 'label': 'Keyword'},
    ]
```

### 3.2 Update Schemas

**File**: `backend/api/schemas.py`

```python
from typing import List, Optional

# Search entry (type + value + count)
class SearchEntry(BaseModel):
    type: str  # Validated against provider's get_search_types()
    value: str
    count: int = Field(default=5, ge=1, le=100)

# Per-provider config
class ProviderConfig(BaseModel):
    enabled: bool = False
    handle: Optional[str] = None  # For Instagram/TikTok
    channel_id: Optional[str] = None  # For YouTube
    channel_handle: Optional[str] = None  # For YouTube @handle
    searches: List[SearchEntry] = []

class SocialProfiles(BaseModel):
    instagram: Optional[ProviderConfig] = None
    tiktok: Optional[ProviderConfig] = None
    youtube: Optional[ProviderConfig] = None
    google_news: Optional[ProviderConfig] = None
    google_search: Optional[ProviderConfig] = None

class BrandConfigCreate(BrandConfigBase):
    social_profiles: SocialProfiles = SocialProfiles()
```

**Validation happens in service layer** using `provider.get_search_type_values()`.

### 3.3 New API Endpoint for Search Types

**File**: `backend/api/routers/providers.py` (NEW)

```python
@router.get("/search-types")
def get_all_search_types():
    """Return search types for all providers - used by frontend"""
    from src.providers.factory import ProviderFactory

    return {
        provider_name: provider_class.get_search_types()
        for provider_name, provider_class in ProviderFactory.get_all_providers().items()
    }
```

This endpoint allows the frontend to dynamically get search types from the backend.

Add `Summary` schema.

### 3.4 Update Brands Router ✅ IMPLEMENTED

**File**: `backend/api/routers/brands.py`

**Implemented endpoints:**
- `POST /` - Creates brand and auto-generates feeds if `social_profiles` provided
- `PATCH/PUT /{brand_id}` - Updates brand and regenerates feeds if `social_profiles` changed
- `GET /{brand_id}/feeds` - Get feeds linked to brand (with `auto_generated_only` filter)
- `POST /{brand_id}/regenerate-feeds` - Regenerate auto-feeds from current social_profiles

**Key implementation:**
```python
# In create_brand:
if brand_data.social_profiles:
    feed_generator = BrandFeedGenerator(db)
    feed_generator.generate_feeds_for_brand(brand)

# In update_brand:
social_profiles_changed = 'social_profiles' in update_data and update_data['social_profiles'] is not None
if social_profiles_changed:
    feed_generator = BrandFeedGenerator(db)
    feed_generator.regenerate_feeds_for_brand(updated_brand)
```

### 3.5 New Summaries Router

**File**: `backend/api/routers/summaries.py` (NEW)

- `GET /` - List summaries for tenant
- `GET /{id}` - Get summary details
- `GET /{id}/download` - Serve PDF file directly (Phase 1) / Return pre-signed URL (Phase 2)
- `DELETE /{id}` - Delete summary record and PDF file

Register in `backend/api/main.py`.

**Download Endpoint (Phase 1)**:
```python
@router.get("/{summary_id}/download")
async def download_summary(summary_id: UUID, ...):
    """Serve PDF file from local filesystem"""
    return FileResponse(
        path=summary.file_path,
        filename=f"{summary.title}.pdf",
        media_type="application/pdf"
    )
```

---

## Phase 4: Frontend Changes

### 4.1 Update Types

**File**: `frontend/src/types/index.ts`

```typescript
// Search entry for any provider
interface SearchEntry {
  type: string;  // Provider-specific: 'profile' | 'hashtag' | 'mentions' | 'user' | 'keyword' | 'channel' | 'search' | 'video' | 'rss_keyword'
  value: string;
  count: number; // 1-100, default from tenant settings
}

// Per-provider configuration
interface ProviderConfig {
  enabled: boolean;
  handle?: string;       // Instagram/TikTok username
  channel_id?: string;   // YouTube channel ID (UCxxx)
  channel_handle?: string; // YouTube @handle
  searches: SearchEntry[];
}

// Social profiles structure (matches JSONB)
interface SocialProfiles {
  instagram?: ProviderConfig;
  tiktok?: ProviderConfig;
  youtube?: ProviderConfig;
  google_news?: ProviderConfig;
  google_search?: ProviderConfig;
}

// Add to Brand interface
interface Brand {
  // ... existing fields
  social_profiles: SocialProfiles;
}

// Summary interface
interface Summary {
  id: string;
  tenant_id: string;
  job_id: string;
  execution_id: string;
  brand_ids: string[];
  title: string;
  executive_summary: string;
  period_start: string;
  period_end: string;
  file_path: string;
  file_size_bytes: number;
  report_count: number;
  generation_status: 'pending' | 'generating' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
}
```

**Search Types**: Fetched dynamically from `GET /api/v1/providers/search-types` endpoint.

```typescript
// frontend/src/api/providers.ts
export async function getSearchTypes(): Promise<Record<string, SearchTypeOption[]>> {
  const response = await apiClient.get('/providers/search-types');
  return response.data;
}

interface SearchTypeOption {
  value: string;
  label: string;
}
```

This ensures frontend always has the correct search types defined by the backend providers.

### 4.2 Update Brands Page Dialog

**File**: `frontend/src/pages/Brands.tsx`

Redesign the brand creation/edit dialog (see `brand_dialog_mockup.html` for visual reference):

**Dialog Structure:**
1. **Basic Info Section**
   - Brand name (required)
   - Aliases (comma-separated)
   - Category dropdown

2. **Provider Cards** (one per platform)
   Each card contains:
   - Header with provider icon, name, and enable/disable toggle
   - Handle input (when applicable - Instagram, TikTok, YouTube)
   - Searches list with:
     - Type dropdown (provider-specific options)
     - Value text input
     - Count number input (1-100)
     - Delete button
   - "Add Search" button to add new search entries

3. **Footer**
   - Cancel button
   - Save Brand button

**Provider-Specific Configurations:**

| Provider | Handle Field | Search Type Options |
|----------|--------------|---------------------|
| Instagram | @username | Profile, Hashtag, Mentions |
| TikTok | @username | User, Hashtag, Keyword |
| YouTube | Channel ID + @handle | Channel, Search, Video |
| Google News | (none) | RSS Keyword |
| Google Search | (none) | Keyword |

### 4.3 Update Jobs Page ✅ IMPLEMENTED

**File**: `frontend/src/pages/Jobs.tsx`

**Implemented features:**
1. Add checkbox: "Generate AI Summary Document" with description
2. **Auto-populate feeds when brand is selected** - When a brand is selected in the job dialog, the system automatically fetches and adds all feeds linked to that brand

**Key code (handleBrandChange):**
```typescript
const handleBrandChange = async (event: SelectChangeEvent<string[]>) => {
  const newBrandIds = typeof value === 'string' ? value.split(',') : value;
  const addedBrandIds = newBrandIds.filter(id => !formData.brand_ids.includes(id));

  // Fetch and add feeds for newly selected brands
  for (const brandId of addedBrandIds) {
    const brandFeeds = await brandsApi.getBrandFeeds(brandId);
    // Add feeds that aren't already selected
  }
};
```

**Helper text added:**
> "Selecting a brand will automatically add its configured feeds"

### 4.4 New Reusable Component

**File**: `frontend/src/components/SummaryList.tsx` (NEW)

Reusable list component showing:
- PDF icon
- Title
- Report count and date
- Download button

Props: `summaries`, `compact?`, `onDownload?`

### 4.5 New Summaries Page

**File**: `frontend/src/pages/Summaries.tsx` (NEW)

Full page using `SummaryList` component.

### 4.6 API Clients

**File**: `frontend/src/api/brands.ts` ✅ UPDATED

Added Brand 360 methods:
```typescript
// Get feeds linked to a brand (Brand 360)
getBrandFeeds: async (brandId: string, autoGeneratedOnly: boolean = false): Promise<Feed[]>

// Regenerate feeds for a brand (Brand 360)
regenerateBrandFeeds: async (brandId: string): Promise<Feed[]>
```

**File**: `frontend/src/api/summaries.ts` (NEW)

- `getSummaries(limit, offset)`
- `getSummary(id)`
- `getDownloadUrl(id)`
- `deleteSummary(id)`

### 4.7 Update Layout

**File**: `frontend/src/components/Layout.tsx`

Add "Summaries" to sidebar menu.

### 4.8 Update Dashboard

**File**: `frontend/src/pages/Dashboard.tsx`

Add "Recent Summaries" card using `SummaryList` (compact mode). See `dashboard_mockup.html` for visual reference.

### 4.9 Update History Page

**File**: `frontend/src/pages/History.tsx`

Show "View Summary" button on executions that have summaries.

### 4.10 Add Route

**File**: `frontend/src/App.tsx`

Add route: `/summaries` -> `<Summaries />`

---

## Phase 5: Configuration

### Environment Variables

Add to `.env`:
```env
# S3 Storage (required for summaries)
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_REGION=us-east-1
AWS_S3_BUCKET=abmc-summaries

# AI Providers
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...

# Default providers for different tasks
AI_BRAND_EXTRACTION_PROVIDER=openai
AI_BRAND_EXTRACTION_MODEL=gpt-4o-mini
AI_SUMMARY_PROVIDER=gemini
AI_SUMMARY_MODEL=gemini-1.5-flash
```

### Dependencies

Add to `requirements.txt`:
```
reportlab>=4.0.0
boto3>=1.28.0
google-generativeai>=0.8.0
```

---

## Critical Files Summary

| File | Status | Changes |
|------|--------|---------|
| `backend/src/models/brand.py` | ✅ | Add `social_profiles` JSONB column |
| `backend/src/models/feed.py` | ✅ | Add `brand_id`, `is_auto_generated` columns |
| `backend/src/models/job.py` | ✅ | Add `generate_summary` boolean |
| `backend/src/models/summary.py` | ✅ | NEW - Summary model |
| `backend/src/providers/base.py` | ✅ | Add `get_search_types()` method |
| `backend/src/providers/*.py` | ✅ | Implement `get_search_types()` for each provider |
| `backend/api/routers/providers.py` | ✅ | NEW - Search types endpoint |
| `backend/src/services/brand_feed_generator.py` | ✅ | NEW - Auto-feed creation from social_profiles |
| `backend/src/services/s3_service.py` | ✅ | NEW - S3 storage with pre-signed URLs |
| `backend/src/services/pdf_generator.py` | ✅ | NEW - reportlab PDF generation |
| `backend/src/services/summary_service.py` | ✅ | NEW - Orchestrates summary generation |
| `backend/src/ai/` | ✅ | Multi-provider AI client (OpenAI, Gemini) |
| `backend/api/schemas.py` | ✅ | Add SearchEntry, ProviderConfig, SocialProfiles, Summary |
| `backend/api/routers/brands.py` | ✅ | Feed generation on create/update, regenerate-feeds endpoint |
| `backend/api/routers/summaries.py` | ✅ | NEW - CRUD endpoints for summaries |
| `frontend/src/types/index.ts` | ✅ | Add SearchEntry, ProviderConfig, SocialProfiles, Summary |
| `frontend/src/pages/Brands.tsx` | ✅ | Redesign dialog with provider cards |
| `frontend/src/pages/Jobs.tsx` | ✅ | generate_summary checkbox + auto-populate feeds from brand |
| `frontend/src/api/brands.ts` | ✅ | Add getBrandFeeds, regenerateBrandFeeds |
| `frontend/src/components/SummaryList.tsx` | 🔄 | NEW - Reusable summary list component |
| `frontend/src/pages/Summaries.tsx` | 🔄 | NEW - Summaries page |
| `frontend/src/api/summaries.ts` | 🔄 | NEW - API client for summaries |
| `frontend/src/components/Layout.tsx` | 🔄 | Add Summaries to sidebar menu |
| `frontend/src/pages/Dashboard.tsx` | 🔄 | Add Recent Summaries section |

---

## Verification

| Test | Status | Description |
|------|--------|-------------|
| Brand Creation | ✅ | Create brand with social profiles, verify feeds auto-generated |
| Search Type Validation | ✅ | Invalid search types rejected by provider |
| Feed Linkage | ✅ | Auto-generated feeds have `brand_id` and `is_auto_generated=true` |
| Job + Brand Selection | ✅ | Selecting brand auto-populates its feeds in job dialog |
| Regenerate Feeds | ✅ | POST /brands/{id}/regenerate-feeds works |
| Job Creation | 🔄 | Create job with `generate_summary: true` |
| Summary Generation | 🔄 | Run job, verify summary PDF created in S3 |
| Download | 🔄 | Test pre-signed URL download |
| Cleanup | 🔄 | Delete summary, verify S3 file removed |

---

## Reusable Infrastructure & Best Practices

### 1. Provider Registry Pattern

Instead of hardcoding provider lists in multiple places, create a central registry:

**File**: `backend/src/providers/registry.py`

```python
class ProviderRegistry:
    """Single source of truth for all provider metadata"""

    _providers: dict[str, type[BaseProvider]] = {}

    @classmethod
    def register(cls, provider_class: type[BaseProvider]):
        """Decorator to register a provider"""
        cls._providers[provider_class.get_provider_name()] = provider_class
        return provider_class

    @classmethod
    def get_all(cls) -> dict[str, type[BaseProvider]]:
        return cls._providers

    @classmethod
    def get(cls, name: str) -> type[BaseProvider] | None:
        return cls._providers.get(name)

    @classmethod
    def get_metadata(cls) -> list[dict]:
        """Return metadata for all providers (for frontend)"""
        return [
            {
                'name': p.get_provider_name(),
                'display_name': p.get_display_name(),
                'search_types': p.get_search_types(),
                'requires_handle': p.requires_handle(),
                'icon': p.get_icon_name(),
            }
            for p in cls._providers.values()
        ]
```

Usage:
```python
@ProviderRegistry.register
class InstagramProvider(BaseProvider):
    ...
```

**Benefits**:
- Add new provider = automatic registration everywhere
- Frontend fetches provider metadata from single endpoint
- No more updating multiple files when adding providers

---

### 2. Base Provider Extended Interface

**File**: `backend/src/providers/base.py`

Add these methods to BaseProvider:

```python
class BaseProvider(ABC):
    # Existing methods...

    @classmethod
    @abstractmethod
    def get_provider_name(cls) -> str:
        """Return provider identifier (e.g., 'INSTAGRAM')"""
        pass

    @classmethod
    def get_display_name(cls) -> str:
        """Human-readable name for UI"""
        return cls.get_provider_name().replace('_', ' ').title()

    @classmethod
    def get_search_types(cls) -> list[dict]:
        """Valid search types: [{'value': 'hashtag', 'label': 'Hashtag'}]"""
        return []

    @classmethod
    def requires_handle(cls) -> bool:
        """Whether this provider needs a handle/username"""
        return False

    @classmethod
    def get_handle_placeholder(cls) -> str:
        """Placeholder text for handle input"""
        return "@username"

    @classmethod
    def get_icon_name(cls) -> str:
        """Icon identifier for frontend"""
        return cls.get_provider_name().lower()

    @classmethod
    def is_social_media(cls) -> bool:
        """Whether this is a social media provider"""
        return False

    @classmethod
    def validate_handle(cls, handle: str) -> tuple[bool, str | None]:
        """Validate handle format, return (is_valid, error_message)"""
        return True, None
```

---

### 3. Frontend Provider Config

**File**: `frontend/src/config/providerConfig.ts`

Fetch once and cache:

```typescript
// Auto-loaded from backend on app init
let providerConfig: ProviderMetadata[] | null = null;

export async function loadProviderConfig(): Promise<void> {
  const response = await apiClient.get('/providers/metadata');
  providerConfig = response.data;
}

export function getProviderConfig(): ProviderMetadata[] {
  if (!providerConfig) throw new Error('Provider config not loaded');
  return providerConfig;
}

export function getProviderByName(name: string): ProviderMetadata | undefined {
  return getProviderConfig().find(p => p.name === name);
}

interface ProviderMetadata {
  name: string;
  display_name: string;
  search_types: { value: string; label: string }[];
  requires_handle: boolean;
  icon: string;
}
```

---

### 4. Reusable Form Components

**File**: `frontend/src/components/forms/ProviderCard.tsx`

Generic provider configuration card:

```typescript
interface ProviderCardProps {
  provider: ProviderMetadata;
  config: ProviderConfig;
  onChange: (config: ProviderConfig) => void;
  defaultSearchCount: number;
}

// Renders: toggle, handle input (if needed), search list
// Used in: Brands dialog, Feed creation, Quick Search
```

**File**: `frontend/src/components/forms/SearchEntryList.tsx`

Reusable search entry editor:

```typescript
interface SearchEntryListProps {
  searchTypes: { value: string; label: string }[];
  entries: SearchEntry[];
  onChange: (entries: SearchEntry[]) => void;
  defaultCount: number;
  maxCount: number;
}

// Renders: list of type/value/count rows with add/remove
// Used in: ProviderCard, Feed edit dialog
```

---

### 5. Status/State Enums Pattern

For any status field, define in one place with display info:

**File**: `backend/src/constants/statuses.py`

```python
class SummaryStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"

    @property
    def display_name(self) -> str:
        return self.value.replace('_', ' ').title()

    @property
    def color(self) -> str:
        """Color hint for frontend"""
        return {
            'pending': 'warning',
            'generating': 'info',
            'completed': 'success',
            'failed': 'error',
        }[self.value]

    @classmethod
    def get_all_metadata(cls) -> list[dict]:
        return [{'value': s.value, 'label': s.display_name, 'color': s.color} for s in cls]
```

**API endpoint**: `GET /api/v1/enums/{enum_name}` returns metadata for any registered enum.

---

### 6. Generic List Component Pattern

**File**: `frontend/src/components/GenericList.tsx`

```typescript
interface GenericListProps<T> {
  items: T[];
  renderItem: (item: T, index: number) => React.ReactNode;
  loading?: boolean;
  emptyMessage?: string;
  compact?: boolean;
}

// SummaryList, ReportList, FeedList all use this base
```

---

### 7. Service Layer Validation Pattern

**File**: `backend/src/services/validation_service.py`

```python
class ValidationService:
    @staticmethod
    def validate_social_profiles(profiles: SocialProfiles) -> list[str]:
        """Validate all social profiles, return list of errors"""
        errors = []
        for provider_name, config in profiles.dict().items():
            if not config or not config.get('enabled'):
                continue

            provider = ProviderRegistry.get(provider_name.upper())
            if not provider:
                errors.append(f"Unknown provider: {provider_name}")
                continue

            # Validate handle if required
            if provider.requires_handle() and not config.get('handle'):
                errors.append(f"{provider.get_display_name()} requires a handle")

            # Validate search types
            valid_types = provider.get_search_type_values()
            for search in config.get('searches', []):
                if search['type'] not in valid_types:
                    errors.append(f"Invalid search type '{search['type']}' for {provider_name}")

        return errors
```

---

### 8. Event-Driven Updates (Future)

Consider adding event hooks for extensibility:

```python
# When brand is created with social_profiles
event_bus.emit('brand.created', brand_id=brand.id, social_profiles=profiles)

# Listeners can react:
# - BrandFeedGenerator listens to create feeds
# - Analytics service listens to update metrics
# - Future: notification service, audit log, etc.
```

---

### Infrastructure Files Summary

| File | Purpose |
|------|---------|
| `backend/src/providers/registry.py` | Provider registration & metadata |
| `backend/src/providers/base.py` | Extended base provider interface |
| `backend/src/constants/statuses.py` | Status enums with metadata |
| `backend/src/services/validation_service.py` | Centralized validation |
| `backend/api/routers/enums.py` | Enum metadata endpoint |
| `frontend/src/config/providerConfig.ts` | Cached provider metadata |
| `frontend/src/components/forms/ProviderCard.tsx` | Reusable provider card |
| `frontend/src/components/forms/SearchEntryList.tsx` | Reusable search list |
| `frontend/src/components/GenericList.tsx` | Base list component |

---

## Implementation Order

1. Database migrations + models
   - Add `social_profiles` JSONB to brand_configs
   - Add `brand_id`, `is_auto_generated` to feed_configs
   - Add `generate_summary` to scheduled_jobs
   - Create summaries table

2. Backend infrastructure
   - Provider registry pattern
   - Extended base provider interface
   - Status enums with metadata

3. Backend services
   - FileStorageService for local file operations
   - PDF generator using reportlab
   - BrandFeedGenerator for auto-feed creation
   - SummaryService for orchestration
   - ValidationService for centralized validation

4. Backend API
   - Update schemas.py with new types and validation
   - Create providers router (search types endpoint)
   - Update brands router with new fields and endpoints
   - Create summaries router

5. Frontend types and API
   - Add TypeScript interfaces
   - Create providers API client
   - Create summaries API client
   - Create providerConfig cache

6. Frontend UI
   - Create reusable components (ProviderCard, SearchEntryList, GenericList)
   - Redesign Brands dialog with provider cards
   - Add SummaryList component
   - Create Summaries page
   - Update Dashboard, History, Layout

7. Integration testing and refinement
