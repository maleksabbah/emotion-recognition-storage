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


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Storage Service...")

    # Init database tables
    await init_db()

    # Ensure S3 bucket exists
    s3 = S3Client()
    s3.ensure_bucket()

    # Start Kafka event producer
    await start_producer()

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