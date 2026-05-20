"""
Per-request DI factories for the storage service.

Same pattern as gateway/orchestrator:
  - DB session per request (commit on success, rollback on failure)
  - Shared S3 clients on app.state from lifespan
"""
from __future__ import annotations

from typing import Any, AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.Config.Database import SessionLocal
from app.Repositories.FileRepository import FileRepository
from app.Repositories.S3Client import S3Client
from app.Services.FileService import FileService


# ─── Per-request DB session ────────────────────────────────────────────

async def get_db_session() -> AsyncIterator[AsyncSession]:
    session = SessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# ─── Shared infra from app.state ───────────────────────────────────────

def get_ops_client(request: Request) -> Any:
    return request.app.state.s3_ops


def get_presign_client(request: Request) -> Any:
    return request.app.state.s3_presign


# ─── Repositories ──────────────────────────────────────────────────────

def get_file_repo(
    session: AsyncSession = Depends(get_db_session),
) -> FileRepository:
    return FileRepository(session)


def get_s3_client(
    ops: Any = Depends(get_ops_client),
    presign: Any = Depends(get_presign_client),
) -> S3Client:
    return S3Client(ops_client=ops, presign_client=presign)


# ─── Services ──────────────────────────────────────────────────────────

def get_file_service(
    files: FileRepository = Depends(get_file_repo),
    s3: S3Client = Depends(get_s3_client),
) -> FileService:
    return FileService(files=files, s3=s3)