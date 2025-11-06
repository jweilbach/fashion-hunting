"""
Pydantic schemas for API request/response validation
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from uuid import UUID


# ============================================================================
# Tenant Schemas
# ============================================================================

class TenantBase(BaseModel):
    name: str
    slug: str
    email: EmailStr
    company_name: Optional[str] = None


class TenantCreate(TenantBase):
    settings: Optional[Dict[str, Any]] = {}


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    company_name: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class Tenant(TenantBase):
    id: UUID
    status: str
    plan: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# User Schemas
# ============================================================================

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: str = "viewer"  # admin, editor, viewer


class UserCreate(UserBase):
    password: str
    tenant_id: UUID


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserChangePassword(BaseModel):
    current_password: str
    new_password: str


class User(UserBase):
    id: UUID
    tenant_id: UUID
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Authentication Schemas
# ============================================================================

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    user_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    email: Optional[str] = None
    role: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User


# ============================================================================
# Report Schemas
# ============================================================================

class ReportBase(BaseModel):
    source: str
    provider: str
    brands: List[str] = []
    title: str
    link: str
    summary: Optional[str] = None
    full_text: Optional[str] = None
    sentiment: Optional[str] = None
    topic: Optional[str] = None
    est_reach: int = 0


class ReportCreate(ReportBase):
    timestamp: datetime
    tenant_id: UUID


class ReportUpdate(BaseModel):
    sentiment: Optional[str] = None
    topic: Optional[str] = None
    brands: Optional[List[str]] = None
    processing_status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class Report(ReportBase):
    id: UUID
    tenant_id: UUID
    timestamp: datetime
    processing_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Feed Config Schemas
# ============================================================================

class FeedConfigBase(BaseModel):
    provider: str  # RSS, TikTok, Instagram
    feed_type: str  # hashtag, keyword, user, rss_url
    feed_value: str  # The actual URL, hashtag, username
    label: Optional[str] = None
    enabled: bool = True
    fetch_count: int = 30
    config: Optional[Dict[str, Any]] = {}


class FeedConfigCreate(FeedConfigBase):
    pass  # tenant_id is set from authenticated user


class FeedConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    label: Optional[str] = None
    fetch_count: Optional[int] = None
    config: Optional[Dict[str, Any]] = None


class FeedConfig(FeedConfigBase):
    id: UUID
    tenant_id: UUID
    last_fetched: Optional[datetime] = None
    last_error: Optional[str] = None
    fetch_count_success: int = 0
    fetch_count_failed: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Brand Config Schemas
# ============================================================================

class BrandConfigBase(BaseModel):
    brand_name: str
    aliases: List[str] = []
    is_known_brand: bool = True
    should_ignore: bool = False
    category: Optional[str] = None  # client, competitor, industry
    notes: Optional[str] = None


class BrandConfigCreate(BrandConfigBase):
    pass  # tenant_id is set from authenticated user


class BrandConfigUpdate(BaseModel):
    aliases: Optional[List[str]] = None
    is_known_brand: Optional[bool] = None
    should_ignore: Optional[bool] = None
    category: Optional[str] = None
    notes: Optional[str] = None


class BrandConfig(BrandConfigBase):
    id: UUID
    tenant_id: UUID
    mention_count: int = 0
    last_mentioned: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Scheduled Job Schemas
# ============================================================================

class ScheduledJobBase(BaseModel):
    job_type: str  # monitor_feeds (main type for brand/feed monitoring)
    schedule_cron: str  # Cron expression (e.g., "0 9 * * *" for daily at 9am, "@manual" for manual only)
    enabled: bool = True
    config: Optional[Dict[str, Any]] = {}  # Contains: name, brand_ids[], feed_ids[]


class ScheduledJobCreate(BaseModel):
    job_type: str = "monitor_feeds"
    schedule_cron: str  # Use "@manual" for manual-only tasks
    enabled: bool = True
    config: Dict[str, Any]  # Required: { name, brand_ids, feed_ids }


class ScheduledJobUpdate(BaseModel):
    schedule_cron: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class ScheduledJob(ScheduledJobBase):
    id: UUID
    tenant_id: UUID
    last_run: Optional[datetime] = None
    last_status: Optional[str] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Job Execution Schemas
# ============================================================================

class JobExecution(BaseModel):
    id: UUID
    job_id: UUID
    tenant_id: UUID
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str  # running, success, failed, partial
    items_processed: int = 0
    items_failed: int = 0
    error_message: Optional[str] = None
    execution_log: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Analytics Schemas
# ============================================================================

class SentimentStats(BaseModel):
    positive: int = 0
    neutral: int = 0
    negative: int = 0
    mixed: int = 0
    unknown: int = 0


class ProviderStats(BaseModel):
    provider: str
    count: int


class DailyCount(BaseModel):
    date: str
    count: int


class TopBrand(BaseModel):
    brand: str
    mentions: int


class AnalyticsSummary(BaseModel):
    total_reports: int
    reports_last_7_days: int
    reports_last_30_days: int
    sentiment_breakdown: SentimentStats
    provider_breakdown: List[ProviderStats]
    daily_counts: List[DailyCount]
    top_brands: List[TopBrand]


# ============================================================================
# Pagination Schemas
# ============================================================================

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int


class ReportListResponse(BaseModel):
    items: List[Report]
    total: int
    page: int
    page_size: int
    pages: int


class BrandListResponse(BaseModel):
    items: List[BrandConfig]
    total: int
    page: int
    page_size: int
    pages: int


class UserListResponse(BaseModel):
    items: List[User]
    total: int
    page: int
    page_size: int
    pages: int


# ============================================================================
# Filter Schemas
# ============================================================================

class ReportFilters(BaseModel):
    provider: Optional[str] = None
    sentiment: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    brands: Optional[List[str]] = None
    search: Optional[str] = None


# ============================================================================
# Health Check Schema
# ============================================================================

class HealthCheck(BaseModel):
    status: str
    version: str
    database: str
    redis: str
    timestamp: datetime


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
