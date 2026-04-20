"""
Storage Service routes — internal API.

Endpoints:
  POST   /internal/presign/upload     → pre-signed upload URL
  POST   /internal/presign/download   → pre-signed download URL
  POST   /internal/save-crops         → decode + upload crops to S3
  POST   /internal/save-output        → decode + upload worker output (e.g. burn result)
  POST   /internal/register           → register an already-uploaded file
  GET    /internal/files/{file_id}    → file metadata
  GET    /internal/files              → list files by session/user/category
  DELETE /internal/files/{file_id}    → delete file + S3 object
  POST   /internal/cleanup            → delete expired files
  GET    /health                      → health check
"""
from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.Config import CLEANUP_EXPIRY_DAYS
from app.Database import get_db
from app.ORM_Models import FileRecord
from app.S3 import S3Client
from app.Events import emit_file_registered, emit_crops_saved, emit_file_deleted, emit_files_cleaned
from app.Schemas import (
    PresignUploadRequest, PresignUploadResponse,
    PresignDownloadRequest, PresignDownloadResponse,
    SaveCropsRequest, SaveCropsResponse,
    SaveOutputRequest,
    RegisterFileRequest,
    FileResponse,
    CleanupResponse,
    HealthResponse,
)

logger = logging.getLogger("storage.routes")
router = APIRouter()


def get_s3() -> S3Client:
    return S3Client()


# ── Pre-signed URLs ────────────────────────────────────

@router.post("/internal/presign/upload", response_model=PresignUploadResponse)
async def presign_upload(
    req: PresignUploadRequest,
    db: AsyncSession = Depends(get_db),
    s3: S3Client = Depends(get_s3),
):
    ext = _extension_from_mime(req.mime_type)
    s3_key = f"uploads/{req.session_id}/{req.file_type}{ext}"
    upload_url = s3.generate_presigned_upload(s3_key, req.mime_type)

    record = FileRecord(
        session_id=req.session_id,
        user_id=req.user_id,
        category="input",
        file_type=req.file_type,
        s3_key=s3_key,
        mime_type=req.mime_type,
        original_filename=req.original_filename,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    await emit_file_registered(record.id, req.session_id, req.file_type, s3_key, req.user_id)

    return PresignUploadResponse(
        file_id=record.id,
        upload_url=upload_url,
        s3_key=s3_key,
    )


@router.post("/internal/presign/download", response_model=PresignDownloadResponse)
async def presign_download(
    req: PresignDownloadRequest,
    db: AsyncSession = Depends(get_db),
    s3: S3Client = Depends(get_s3),
):
    result = await db.execute(select(FileRecord).where(FileRecord.id == req.file_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    download_url = s3.generate_presigned_download(record.s3_key)
    return PresignDownloadResponse(
        download_url=download_url,
        file_id=record.id,
        file_type=record.file_type,
    )


# ── Crop Storage ───────────────────────────────────────

@router.post("/internal/save-crops", response_model=SaveCropsResponse)
async def save_crops(
    req: SaveCropsRequest,
    db: AsyncSession = Depends(get_db),
    s3: S3Client = Depends(get_s3),
):
    file_ids = {}
    for crop_name, crop_b64 in req.crops.items():
        crop_bytes = base64.b64decode(crop_b64)
        s3_key = (
            f"crops/{req.session_id}/"
            f"frame_{req.frame_index}/"
            f"det_{req.detection_index}/"
            f"{crop_name}.jpg"
        )
        size = s3.upload_bytes(s3_key, crop_bytes, "image/jpeg")

        record = FileRecord(
            session_id=req.session_id,
            user_id=req.user_id,
            category="crop",
            file_type=crop_name,
            s3_key=s3_key,
            size_bytes=size,
            mime_type="image/jpeg",
            metadata_json=json.dumps({
                "frame_index": req.frame_index,
                "detection_index": req.detection_index,
            }),
        )
        db.add(record)
        await db.flush()
        file_ids[crop_name] = record.id

    await db.commit()
    await emit_crops_saved(req.session_id, req.frame_index, req.detection_index, file_ids, req.user_id)

    return SaveCropsResponse(
        session_id=req.session_id,
        frame_index=req.frame_index,
        detection_index=req.detection_index,
        file_ids=file_ids,
    )


# ── Worker Output Storage ──────────────────────────────

@router.post("/internal/save-output", response_model=FileResponse)
async def save_output(
    req: SaveOutputRequest,
    db: AsyncSession = Depends(get_db),
    s3: S3Client = Depends(get_s3),
):
    """Decode base64 bytes, upload to S3 at the caller-provided key, register in DB.

    Used by workers (burner, etc.) to hand off their output to storage.
    The caller provides the S3 key — storage does not invent it. This keeps
    path authority with the orchestrator while making storage the sole
    gatekeeper of MinIO writes and the files registry.
    """
    try:
        data = base64.b64decode(req.data_b64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 data: {e}")

    size = s3.upload_bytes(req.s3_key, data, req.mime_type)

    record = FileRecord(
        session_id=req.session_id,
        user_id=req.user_id,
        category=req.category,
        file_type=req.file_type,
        s3_key=req.s3_key,
        size_bytes=size,
        mime_type=req.mime_type,
        original_filename=req.original_filename,
        metadata_json=req.metadata_json,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    await emit_file_registered(record.id, req.session_id, req.file_type, req.s3_key, req.user_id)
    logger.info("Saved output: session=%s key=%s size=%d bytes", req.session_id, req.s3_key, size)
    return record


# ── File Registration ──────────────────────────────────

@router.post("/internal/register", response_model=FileResponse)
async def register_file(
    req: RegisterFileRequest,
    db: AsyncSession = Depends(get_db),
):
    record = FileRecord(
        session_id=req.session_id,
        user_id=req.user_id,
        category=req.category,
        file_type=req.file_type,
        s3_key=req.s3_key,
        size_bytes=req.size_bytes,
        mime_type=req.mime_type,
        original_filename=req.original_filename,
        metadata_json=req.metadata_json,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    await emit_file_registered(record.id, req.session_id, req.file_type, req.s3_key, req.user_id)
    return record


# ── File Queries ───────────────────────────────────────

@router.get("/internal/files/{file_id}", response_model=FileResponse)
async def get_file(file_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FileRecord).where(FileRecord.id == file_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    return record


@router.get("/internal/files", response_model=list[FileResponse])
async def list_files(
    session_id: str | None = None,
    user_id: str | None = None,
    category: str | None = None,
    file_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(FileRecord)
    if session_id:
        query = query.where(FileRecord.session_id == session_id)
    if user_id:
        query = query.where(FileRecord.user_id == user_id)
    if category:
        query = query.where(FileRecord.category == category)
    if file_type:
        query = query.where(FileRecord.file_type == file_type)

    query = query.order_by(FileRecord.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


# ── File Deletion ──────────────────────────────────────

@router.delete("/internal/files/{file_id}")
async def delete_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    s3: S3Client = Depends(get_s3),
):
    result = await db.execute(select(FileRecord).where(FileRecord.id == file_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    s3.delete_object(record.s3_key)
    await db.delete(record)
    await db.commit()
    await emit_file_deleted(file_id, record.s3_key)
    return {"detail": "File deleted", "file_id": file_id}


# ── Cleanup ────────────────────────────────────────────

@router.post("/internal/cleanup", response_model=CleanupResponse)
async def cleanup_expired(
    db: AsyncSession = Depends(get_db),
    s3: S3Client = Depends(get_s3),
):
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(FileRecord).where(
            FileRecord.expires_at.isnot(None),
            FileRecord.expires_at < now,
        )
    )
    expired = result.scalars().all()
    if not expired:
        return CleanupResponse(deleted_count=0)

    s3_keys = [f.s3_key for f in expired]
    s3.delete_objects(s3_keys)

    expired_ids = [f.id for f in expired]
    await db.execute(sa_delete(FileRecord).where(FileRecord.id.in_(expired_ids)))
    await db.commit()

    await emit_files_cleaned(len(expired), s3_keys)
    logger.info("Cleaned up %d expired files", len(expired))
    return CleanupResponse(deleted_count=len(expired))


# ── Health ─────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health(
    db: AsyncSession = Depends(get_db),
    s3: S3Client = Depends(get_s3),
):
    db_ok = False
    try:
        await db.execute(select(1))
        db_ok = True
    except Exception:
        pass

    s3_ok = s3.check_connection()
    status = "healthy" if (db_ok and s3_ok) else "degraded"
    return HealthResponse(status=status, s3_connected=s3_ok, db_connected=db_ok)


# ── Helpers ────────────────────────────────────────────

def _extension_from_mime(mime_type: str) -> str:
    mapping = {
        "video/mp4": ".mp4",
        "video/avi": ".avi",
        "video/webm": ".webm",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "application/json": ".json",
    }
    return mapping.get(mime_type, "")
