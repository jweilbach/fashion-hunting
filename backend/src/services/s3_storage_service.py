"""
S3 Storage Service - AWS S3 storage for PDF summaries

Provides cloud storage for PDF files with pre-signed URL support
for secure, time-limited downloads.
"""
import os
import re
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)


def sanitize_filename(title: str) -> str:
    """Convert title to safe filename."""
    # Replace spaces and special chars with underscores
    safe = re.sub(r'[^\w\s-]', '', title)
    safe = re.sub(r'[-\s]+', '_', safe)
    return safe.strip('_')[:100]  # Limit length


class S3StorageService:
    """
    AWS S3 storage service for PDF summaries.

    Storage structure:
        s3://{bucket}/summaries/{tenant_id}/{title}_{YYYY-MM-DD}.pdf

    Features:
    - Pre-signed URLs for secure downloads
    - Automatic content-type handling
    - Configurable URL expiration
    - Human-readable filenames with dates
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        region: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        presigned_url_expiry: int = 3600  # 1 hour default
    ):
        """
        Initialize S3 storage service.

        Args:
            bucket_name: S3 bucket name (default from S3_BUCKET_NAME env)
            region: AWS region (default from AWS_REGION env)
            access_key_id: AWS access key (default from AWS_ACCESS_KEY_ID env)
            secret_access_key: AWS secret key (default from AWS_SECRET_ACCESS_KEY env)
            presigned_url_expiry: Seconds until pre-signed URLs expire
        """
        self.bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME')
        self.region = region or os.getenv('AWS_REGION', 'us-east-1')
        self.presigned_url_expiry = presigned_url_expiry

        # Initialize S3 client
        self._s3_client = None
        self._access_key_id = access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
        self._secret_access_key = secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY')

        if not self.bucket_name:
            logger.warning("S3_BUCKET_NAME not configured - S3 storage unavailable")
        else:
            logger.info(f"S3StorageService initialized with bucket: {self.bucket_name}")

    @property
    def s3_client(self):
        """Lazy initialization of S3 client."""
        if self._s3_client is None:
            if self._access_key_id and self._secret_access_key:
                self._s3_client = boto3.client(
                    's3',
                    region_name=self.region,
                    aws_access_key_id=self._access_key_id,
                    aws_secret_access_key=self._secret_access_key
                )
            else:
                # Use default credentials (IAM role, environment, etc.)
                self._s3_client = boto3.client('s3', region_name=self.region)
        return self._s3_client

    def is_available(self) -> bool:
        """Check if S3 storage is properly configured and accessible."""
        if not self.bucket_name:
            return False

        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except (ClientError, NoCredentialsError) as e:
            logger.warning(f"S3 bucket not accessible: {e}")
            return False

    def get_s3_key(
        self,
        tenant_id: UUID,
        summary_id: UUID,
        title: Optional[str] = None,
        created_at: Optional[datetime] = None
    ) -> str:
        """
        Get the S3 key (path) for a summary PDF.

        Args:
            tenant_id: Tenant UUID
            summary_id: Summary UUID
            title: Optional summary title for readable filename
            created_at: Optional creation date for filename

        Returns:
            S3 key string like: summaries/{tenant_id}/Media_Coverage_Summary_2025-01-15.pdf
        """
        if title:
            safe_title = sanitize_filename(title)
            date_str = (created_at or datetime.now()).strftime('%Y-%m-%d')
            filename = f"{safe_title}_{date_str}.pdf"
        else:
            # Fallback to summary_id if no title provided
            filename = f"{summary_id}.pdf"

        return f"summaries/{tenant_id}/{filename}"

    def save_pdf(
        self,
        tenant_id: UUID,
        summary_id: UUID,
        pdf_bytes: bytes,
        title: Optional[str] = None,
        created_at: Optional[datetime] = None
    ) -> str:
        """
        Upload PDF to S3.

        Args:
            tenant_id: Tenant UUID
            summary_id: Summary UUID
            pdf_bytes: PDF file content as bytes
            title: Optional summary title for readable filename
            created_at: Optional creation date for filename

        Returns:
            S3 key of the uploaded file
        """
        s3_key = self.get_s3_key(tenant_id, summary_id, title, created_at)

        # Create a nice download filename
        if title:
            safe_title = sanitize_filename(title)
            date_str = (created_at or datetime.now()).strftime('%Y-%m-%d')
            download_filename = f"{safe_title}_{date_str}.pdf"
        else:
            download_filename = f"{summary_id}.pdf"

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=pdf_bytes,
                ContentType='application/pdf',
                ContentDisposition=f'attachment; filename="{download_filename}"'
            )
            logger.info(f"Uploaded PDF to s3://{self.bucket_name}/{s3_key} ({len(pdf_bytes)} bytes)")
            return s3_key
        except ClientError as e:
            logger.error(f"Failed to upload PDF to S3: {e}")
            raise

    def read_pdf(self, tenant_id: UUID, summary_id: UUID) -> Optional[bytes]:
        """
        Download PDF from S3.

        Args:
            tenant_id: Tenant UUID
            summary_id: Summary UUID

        Returns:
            PDF file content as bytes, or None if not found
        """
        s3_key = self.get_s3_key(tenant_id, summary_id)

        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"PDF not found at s3://{self.bucket_name}/{s3_key}")
                return None
            logger.error(f"Failed to download PDF from S3: {e}")
            raise

    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3.

        Args:
            s3_key: S3 key of the file to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            logger.info(f"Deleted s3://{self.bucket_name}/{s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete from S3: {e}")
            return False

    def delete_summary_pdf(self, tenant_id: UUID, summary_id: UUID) -> bool:
        """
        Delete a summary's PDF file from S3.

        Args:
            tenant_id: Tenant UUID
            summary_id: Summary UUID

        Returns:
            True if deleted, False if not found
        """
        s3_key = self.get_s3_key(tenant_id, summary_id)
        return self.delete_file(s3_key)

    def file_exists(self, tenant_id: UUID, summary_id: UUID) -> bool:
        """
        Check if a summary PDF exists in S3.

        Args:
            tenant_id: Tenant UUID
            summary_id: Summary UUID

        Returns:
            True if file exists, False otherwise
        """
        s3_key = self.get_s3_key(tenant_id, summary_id)

        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise

    def get_file_size(self, tenant_id: UUID, summary_id: UUID) -> Optional[int]:
        """
        Get the size of a summary PDF in S3.

        Args:
            tenant_id: Tenant UUID
            summary_id: Summary UUID

        Returns:
            File size in bytes, or None if file doesn't exist
        """
        s3_key = self.get_s3_key(tenant_id, summary_id)

        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return response['ContentLength']
        except ClientError:
            return None

    def get_download_url(self, summary_id: UUID, tenant_id: Optional[UUID] = None) -> str:
        """
        Generate a pre-signed URL for downloading a summary PDF.

        Args:
            summary_id: Summary UUID
            tenant_id: Optional tenant UUID (for building S3 key)

        Returns:
            Pre-signed URL for downloading the PDF
        """
        if tenant_id:
            s3_key = self.get_s3_key(tenant_id, summary_id)
        else:
            # If no tenant_id, we need to look it up or use a pattern
            # For now, return API endpoint as fallback
            return f"/api/v1/summaries/{summary_id}/download"

        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key,
                    'ResponseContentType': 'application/pdf'
                },
                ExpiresIn=self.presigned_url_expiry
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate pre-signed URL: {e}")
            # Fallback to API endpoint
            return f"/api/v1/summaries/{summary_id}/download"

    def cleanup_tenant_files(self, tenant_id: UUID) -> int:
        """
        Delete all files for a tenant from S3.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Number of files deleted
        """
        prefix = f"summaries/{tenant_id}/"

        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            count = 0

            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                objects = page.get('Contents', [])
                if not objects:
                    continue

                # Batch delete
                delete_keys = [{'Key': obj['Key']} for obj in objects]
                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': delete_keys}
                )
                count += len(delete_keys)

            logger.info(f"Cleaned up {count} files for tenant {tenant_id} from S3")
            return count

        except ClientError as e:
            logger.error(f"Failed to cleanup tenant files from S3: {e}")
            return 0
