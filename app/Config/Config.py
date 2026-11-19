"""
Storage service configuration.

Two-endpoint S3 config is intentional:
  S3_INTERNAL_ENDPOINT  → boto3 ops (PUT/GET/HEAD) over the docker network
  S3_PUBLIC_ENDPOINT    → embedded in presigned URLs handed to the browser
"""
from __future__ import annotations

import os
import re


# ─── PostgreSQL (storage_db) ───────────────────────────────────────────

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "emotion")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
STORAGE_DB = os.getenv("STORAGE_DB", "storage_db")
def _asyncpg_url(url: str) -> str:
    """
    Normalise a provider URL for SQLAlchemy + asyncpg. Railway/Supabase hand
    out postgres:// or postgresql://; asyncpg also rejects libpq's sslmode=,
    so map it to its own ssl= parameter.
    """
    url = re.sub(r"^postgres(ql)?://", "postgresql+asyncpg://", url)
    return re.sub(r"([?&])sslmode=", r"\1ssl=", url)


_DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not _DATABASE_URL and not POSTGRES_PASSWORD:
    raise RuntimeError("Set DATABASE_URL, or POSTGRES_PASSWORD with the POSTGRES_* parts")

STORAGE_DB_URL = _asyncpg_url(_DATABASE_URL) if _DATABASE_URL else (
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{STORAGE_DB}"
)

# ─── S3 / MinIO ────────────────────────────────────────────────────────

S3_INTERNAL_ENDPOINT = os.getenv("S3_INTERNAL_ENDPOINT", "http://minio:9000")
S3_PUBLIC_ENDPOINT = os.getenv("S3_PUBLIC_ENDPOINT", "http://localhost:9000")
S3_BUCKET = os.getenv("S3_BUCKET", "emotion")
S3_ACCESS_KEY = os.environ["S3_ACCESS_KEY"]
S3_SECRET_KEY = os.environ["S3_SECRET_KEY"]
S3_REGION = os.getenv("S3_REGION", "us-east-1")

PRESIGN_UPLOAD_TTL_SECONDS = int(os.getenv("PRESIGN_UPLOAD_TTL_SECONDS", "900"))   # 15m
PRESIGN_DOWNLOAD_TTL_SECONDS = int(os.getenv("PRESIGN_DOWNLOAD_TTL_SECONDS", "3600"))  # 1h


# ─── CORS ──────────────────────────────────────────────────────────────

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")