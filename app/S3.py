"""
S3 client wrapper — handles all MinIO/S3 operations.

- Upload bytes
- Generate pre-signed upload URLs
- Generate pre-signed download URLs
- Delete objects
- Check connectivity
"""
from __future__ import annotations

import logging
from typing import Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from app.Config import (
    S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY,
    S3_BUCKET, S3_REGION,
    PRESIGN_UPLOAD_EXPIRY, PRESIGN_DOWNLOAD_EXPIRY,
)

logger = logging.getLogger("storage.s3")

class S3Client:
    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            region_name=S3_REGION,
        )
        self.bucket = S3_BUCKET
    def ensure_bucket(self) -> None:
        """Create the bucket if it doesn't exist."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self.bucket)
            logger.info("Created bucket: %s", self.bucket)
    def upload_bytes(self,s3_key: str, data: bytes, content_type:str = "application/octet-stream") -> None:
        """Upload raw bytes to S3. Returns size in bytes."""
        self.client.put_object(
            Bucket=self.bucket,
            Key=s3_key,
            Body=data,
            ContentType=content_type,

        )
        logger.debug("Uploaded %d bytes to %s", len(data), s3_key)
        return len(data)

    def generate_presigned_upload(self, s3_key: str, content_type: str = "application/octet-stream") -> str:
        """Generate a pre-signed URL for uploading directly to S3."""
        url = self.client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket,
                    "Key": s3_key,
                    "ContentType": content_type,
                    },
            ExpiresIn=PRESIGN_UPLOAD_EXPIRY,
        )
        return url
    def generate_presigned_download(self, s3_key: str) -> str:
        """Generate a pre-signed URL for downloading from S3."""
        url = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket,
                    "Key": s3_key,},
            ExpiresIn=PRESIGN_DOWNLOAD_EXPIRY,

        )
        return url
    def delete_object(self, s3_key: str) -> None:
        """Delete a single object from S3."""
        self.client.delete_object(Bucket=self.bucket, Key=s3_key)
        logger.debug("Deleted object %s", s3_key)
    def delete_objects(self, s3_keys: list[str]) -> None:
        """Bulk delete objects. Returns count deleted."""
        if not s3_keys:
            return 0

        # S3 bulk delete supports max 1000 keys per request
        deleted = 0
        for i in range(0,len(s3_keys),1000):
            batch = s3_keys[i:i+1000]
            objects = [{"Key":k} for k in batch]
            self.client.delete_objects(
                Bucket=self.bucket,
                Delete={"Objects": objects},
            )
            deleted += len(objects)
        logger.info("Bulk deleted %d objects", deleted)
        return deleted

    def check_connection(self) -> bool:
        """Check if S3 is reachable."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except (ClientError, NoCredentialsError, Exception):
            return False













