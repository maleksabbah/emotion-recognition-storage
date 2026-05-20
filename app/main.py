"""
Storage service entry point.

Builds the FastAPI app: lifespan creates the two boto3 clients (ops +
presign), CORS, domain exception handler, mounts health + file routers.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.Config import CORS_ORIGINS, make_ops_client, make_presign_client
from app.Exceptions import register_exception_handlers
from app.Routes import file_router, health_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("storage")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting storage...")
    app.state.s3_ops = make_ops_client()
    app.state.s3_presign = make_presign_client()
    logger.info("Storage ready")

    yield

    logger.info("Shutting down...")
    # boto3 clients close on garbage collection — nothing to await


app = FastAPI(
    title="Emotion Recognition Storage",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(health_router)
app.include_router(file_router)