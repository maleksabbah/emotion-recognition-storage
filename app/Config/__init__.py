"""
Config package — env vars + external-system factories.
"""
from app.Config.Config import (
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
    STORAGE_DB,
    STORAGE_DB_URL,
    S3_INTERNAL_ENDPOINT,
    S3_PUBLIC_ENDPOINT,
    S3_BUCKET,
    S3_ACCESS_KEY,
    S3_SECRET_KEY,
    S3_REGION,
    PRESIGN_UPLOAD_TTL_SECONDS,
    PRESIGN_DOWNLOAD_TTL_SECONDS,
    CORS_ORIGINS,
)
from app.Config.Database import engine, SessionLocal
from app.Config.S3 import make_ops_client, make_presign_client

__all__ = [
    "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_PASSWORD",
    "STORAGE_DB", "STORAGE_DB_URL",
    "S3_INTERNAL_ENDPOINT", "S3_PUBLIC_ENDPOINT", "S3_BUCKET",
    "S3_ACCESS_KEY", "S3_SECRET_KEY", "S3_REGION",
    "PRESIGN_UPLOAD_TTL_SECONDS", "PRESIGN_DOWNLOAD_TTL_SECONDS",
    "CORS_ORIGINS",
    "engine", "SessionLocal",
    "make_ops_client", "make_presign_client",
]