"""
Storage Service — FastAPI application.

Manages all S3/MinIO operations and file metadata in storage_db.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.Database import init_db
from app.S3 import S3Client
from app.Events import start_producer, stop_producer
from app.Routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("storage")


_s3_ok = False
_db_ok = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _s3_ok, _db_ok
    logger.info("Starting Storage Service...")

    # Init database tables
    try:
        await init_db()
        _db_ok = True
        logger.info("  PostgreSQL connected")
    except Exception as e:
        logger.error("  PostgreSQL failed: %s", e)

    # Ensure S3 bucket exists
    try:
        s3 = S3Client()
        s3.ensure_bucket()
        _s3_ok = True
        logger.info("  S3/MinIO connected")
    except Exception as e:
        logger.error("  S3/MinIO failed: %s", e)

    # Start Kafka event producer
    try:
        await start_producer()
        logger.info("  Kafka producer started")
    except Exception as e:
        logger.warning("  Kafka producer failed (non-fatal): %s", e)

    logger.info("Storage Service ready")
    yield

    # Shutdown
    await stop_producer()
    logger.info("Storage Service stopped")


app = FastAPI(
    title="Emotion Recognition Storage Service",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(router)


# Health check — root level, used by Docker health check
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "storage",
        "postgres": _db_ok,
        "s3": _s3_ok,
    }