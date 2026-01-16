"""
File Storage Service - Unified storage abstraction for PDF summaries

Automatically selects between local filesystem and S3 based on configuration.
Prefers S3 if configured, falls back to local storage.
"""
import os
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Union
from uuid import UUID

logger = logging.getLogger(__name__)


def sanitize_filename(title: str) -> str:
    """Convert title to safe filename."""
    safe = re.sub(r'[^\w\s-]', '', title)
    safe = re.sub(r'[-\s]+', '_', safe)
    return safe.strip('_')[:100]

# Storage backend constants
STORAGE_LOCAL = 'local'
STORAGE_S3 = 's3'


class FileStorageService:
    """
    Unified file storage service for PDF summaries.

    Automatically selects storage backend:
    - S3 if AWS credentials and bucket are configured
    - Local filesystem as fallback

    Storage structures:
        Local: {base_path}/{tenant_id}/{summary_id}.pdf
        S3: s3://{bucket}/summaries/{tenant_id}/{summary_id}.pdf
    """

    def __init__(
        self,
        base_path: Optional[str] = None,
        force_backend: Optional[str] = None
    ):
        """
        Initialize file storage service.

        Args:
            base_path: Base directory for local storage.
                      Defaults to SUMMARIES_DIR env var or 'summaries'
            force_backend: Force a specific backend ('local' or 's3')
        """
        self._s3_service = None
        self._storage_backend = None

        # Local storage config
        self.base_path = Path(
            base_path or
            os.getenv('SUMMARIES_DIR', 'summaries')
        )

        # Determine storage backend
        if force_backend:
            self._storage_backend = force_backend
        else:
            self._storage_backend = self._detect_backend()

        # Initialize based on backend
        if self._storage_backend == STORAGE_S3:
            self._init_s3()
        else:
            self._init_local()

        logger.info(f"FileStorageService initialized with backend: {self._storage_backend}")

    def _detect_backend(self) -> str:
        """Detect which storage backend to use based on environment."""
        # Check for S3 configuration
        s3_bucket = os.getenv('S3_BUCKET_NAME')
        aws_configured = bool(
            os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY')
        ) or bool(os.getenv('AWS_PROFILE'))

        if s3_bucket and aws_configured:
            # Try to import boto3 and verify S3 is accessible
            try:
                from services.s3_storage_service import S3StorageService
                test_service = S3StorageService()
                if test_service.is_available():
                    return STORAGE_S3
                else:
                    logger.warning("S3 configured but bucket not accessible, falling back to local")
            except ImportError:
                logger.warning("boto3 not installed, falling back to local storage")
            except Exception as e:
                logger.warning(f"S3 initialization failed: {e}, falling back to local")

        return STORAGE_LOCAL

    def _init_s3(self):
        """Initialize S3 storage backend."""
        from services.s3_storage_service import S3StorageService
        self._s3_service = S3StorageService()

    def _init_local(self):
        """Initialize local storage backend."""
        self.base_path.mkdir(parents=True, exist_ok=True)

    @property
    def storage_backend(self) -> str:
        """Get current storage backend type."""
        return self._storage_backend

    @property
    def is_s3(self) -> bool:
        """Check if using S3 storage."""
        return self._storage_backend == STORAGE_S3

    # ==================== Local Storage Methods ====================

    def get_tenant_dir(self, tenant_id: UUID) -> Path:
        """Get the directory path for a tenant's files (local storage only)."""
        tenant_dir = self.base_path / str(tenant_id)
        tenant_dir.mkdir(parents=True, exist_ok=True)
        return tenant_dir

    def get_file_path(
        self,
        tenant_id: UUID,
        summary_id: UUID,
        title: Optional[str] = None,
        created_at: Optional[datetime] = None
    ) -> Path:
        """
        Get the full path for a summary PDF file (local storage only).

        Args:
            tenant_id: Tenant UUID
            summary_id: Summary UUID
            title: Optional summary title for readable filename
            created_at: Optional creation date for filename

        Returns:
            Path object to the PDF file
        """
        if title:
            safe_title = sanitize_filename(title)
            date_str = (created_at or datetime.now()).strftime('%Y-%m-%d')
            filename = f"{safe_title}_{date_str}.pdf"
        else:
            filename = f"{summary_id}.pdf"

        return self.get_tenant_dir(tenant_id) / filename

    # ==================== Unified Interface Methods ====================

    def save_pdf(
        self,
        tenant_id: UUID,
        summary_id: UUID,
        pdf_bytes: bytes,
        title: Optional[str] = None,
        created_at: Optional[datetime] = None
    ) -> str:
        """
        Save PDF bytes to storage (S3 or local).

        Args:
            tenant_id: Tenant UUID
            summary_id: Summary UUID
            pdf_bytes: PDF file content as bytes
            title: Optional summary title for readable filename
            created_at: Optional creation date for filename

        Returns:
            String path/key to the saved file
        """
        if self.is_s3:
            return self._s3_service.save_pdf(tenant_id, summary_id, pdf_bytes, title, created_at)

        # Local storage
        file_path = self.get_file_path(tenant_id, summary_id, title, created_at)

        try:
            file_path.write_bytes(pdf_bytes)
            logger.info(f"Saved PDF to {file_path} ({len(pdf_bytes)} bytes)")
            return str(file_path)
        except Exception as e:
            logger.error(f"Failed to save PDF to {file_path}: {e}")
            raise

    def read_pdf(self, tenant_id: UUID, summary_id: UUID) -> Optional[bytes]:
        """
        Read PDF bytes from storage (S3 or local).

        Args:
            tenant_id: Tenant UUID
            summary_id: Summary UUID

        Returns:
            PDF file content as bytes, or None if not found
        """
        if self.is_s3:
            return self._s3_service.read_pdf(tenant_id, summary_id)

        # Local storage
        file_path = self.get_file_path(tenant_id, summary_id)

        if not file_path.exists():
            logger.warning(f"PDF not found at {file_path}")
            return None

        try:
            return file_path.read_bytes()
        except Exception as e:
            logger.error(f"Failed to read PDF from {file_path}: {e}")
            raise

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from storage.

        Args:
            file_path: Path/key to the file to delete

        Returns:
            True if file was deleted, False if it didn't exist
        """
        if self.is_s3:
            return self._s3_service.delete_file(file_path)

        # Local storage
        path = Path(file_path)

        if not path.exists():
            logger.warning(f"File not found for deletion: {file_path}")
            return False

        try:
            path.unlink()
            logger.info(f"Deleted file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            raise

    def delete_summary_pdf(self, tenant_id: UUID, summary_id: UUID) -> bool:
        """
        Delete a summary's PDF file.

        Args:
            tenant_id: Tenant UUID
            summary_id: Summary UUID

        Returns:
            True if file was deleted, False if it didn't exist
        """
        if self.is_s3:
            return self._s3_service.delete_summary_pdf(tenant_id, summary_id)

        file_path = self.get_file_path(tenant_id, summary_id)
        return self.delete_file(str(file_path))

    def file_exists(self, tenant_id: UUID, summary_id: UUID) -> bool:
        """
        Check if a summary PDF file exists.

        Args:
            tenant_id: Tenant UUID
            summary_id: Summary UUID

        Returns:
            True if file exists, False otherwise
        """
        if self.is_s3:
            return self._s3_service.file_exists(tenant_id, summary_id)

        file_path = self.get_file_path(tenant_id, summary_id)
        return file_path.exists()

    def get_file_size(self, tenant_id: UUID, summary_id: UUID) -> Optional[int]:
        """
        Get the size of a summary PDF file in bytes.

        Args:
            tenant_id: Tenant UUID
            summary_id: Summary UUID

        Returns:
            File size in bytes, or None if file doesn't exist
        """
        if self.is_s3:
            return self._s3_service.get_file_size(tenant_id, summary_id)

        file_path = self.get_file_path(tenant_id, summary_id)

        if not file_path.exists():
            return None

        return file_path.stat().st_size

    def get_download_url(self, summary_id: UUID, tenant_id: Optional[UUID] = None) -> str:
        """
        Get URL for downloading a summary PDF.

        For S3: Returns a pre-signed URL (time-limited direct access)
        For Local: Returns API endpoint path

        Args:
            summary_id: Summary UUID
            tenant_id: Optional tenant UUID (needed for S3 pre-signed URLs)

        Returns:
            URL string for downloading the PDF
        """
        if self.is_s3 and tenant_id:
            return self._s3_service.get_download_url(summary_id, tenant_id)

        # API endpoint for local storage (or S3 fallback)
        return f"/api/v1/summaries/{summary_id}/download"

    def cleanup_tenant_files(self, tenant_id: UUID) -> int:
        """
        Delete all files for a tenant (used when tenant is deleted).

        Args:
            tenant_id: Tenant UUID

        Returns:
            Number of files deleted
        """
        if self.is_s3:
            return self._s3_service.cleanup_tenant_files(tenant_id)

        # Local storage
        tenant_dir = self.base_path / str(tenant_id)

        if not tenant_dir.exists():
            return 0

        count = 0
        for pdf_file in tenant_dir.glob("*.pdf"):
            try:
                pdf_file.unlink()
                count += 1
            except Exception as e:
                logger.error(f"Failed to delete {pdf_file}: {e}")

        # Try to remove the tenant directory if empty
        try:
            tenant_dir.rmdir()
        except OSError:
            pass  # Directory not empty or other error

        logger.info(f"Cleaned up {count} files for tenant {tenant_id}")
        return count
