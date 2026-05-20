"""
boto3 S3 client factories.

ops_client       → uses S3_INTERNAL_ENDPOINT — for PUT/GET/HEAD inside the
                   docker network
presign_client   → uses S3_PUBLIC_ENDPOINT — signs URLs the browser will hit

Both live on app.state, built once during lifespan.
"""
from __future__ import annotations

import boto3
from botocore.client import Config as BotoConfig

from app.Config.Config import (
    S3_ACCESS_KEY,
    S3_INTERNAL_ENDPOINT,
    S3_PUBLIC_ENDPOINT,
    S3_REGION,
    S3_SECRET_KEY,
)


def make_ops_client():
    return boto3.client(
        "s3",
        endpoint_url=S3_INTERNAL_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
        config=BotoConfig(signature_version="s3v4"),
    )


def make_presign_client():
    return boto3.client(
        "s3",
        endpoint_url=S3_PUBLIC_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
        config=BotoConfig(signature_version="s3v4"),
    )