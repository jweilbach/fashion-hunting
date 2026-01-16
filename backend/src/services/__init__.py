"""
Content processing services
"""
from services.base_processor import BaseContentProcessor
from services.article_processor import ArticleProcessor
from services.social_media_processor import SocialMediaProcessor
from services.processor_factory import ProcessorFactory
from services.job_execution_service import JobExecutionService, JobExecutionResult
from services.analytics_service import AnalyticsService

# Brand 360 services
from services.file_storage_service import FileStorageService
from services.pdf_generator import PDFGenerator
from services.summary_service import SummaryService
from services.brand_feed_generator import BrandFeedGenerator

# Optional S3 service (requires boto3)
try:
    from services.s3_storage_service import S3StorageService
except ImportError:
    S3StorageService = None

__all__ = [
    'BaseContentProcessor',
    'ArticleProcessor',
    'SocialMediaProcessor',
    'ProcessorFactory',
    'JobExecutionService',
    'JobExecutionResult',
    'AnalyticsService',
    # Brand 360
    'FileStorageService',
    'S3StorageService',
    'PDFGenerator',
    'SummaryService',
    'BrandFeedGenerator',
]
