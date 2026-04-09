"""
Pydantic schemas for Storage Service API.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ── Requests ───────────────────────────────────────────

class PresignUploadRequest(BaseModel):
    session_id: str
    file_type: str          # e.g. "video_upload", "image_upload"
    mime_type: str           # e.g. "video/mp4", "image/jpeg"
    original_filename: Optional[str] = None
    user_id: Optional[str] = None


class PresignDownloadRequest(BaseModel):
    file_id: str


class SaveCropsRequest(BaseModel):
    session_id: str
    frame_index: int
    detection_index: int
    crops: dict[str, str]    # {"face": b64, "eyes": b64, ...}
    user_id: Optional[str] = None


class RegisterFileRequest(BaseModel):
    session_id: str
    category: str
    file_type: str
    s3_key: str
    size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    original_filename: Optional[str] = None
    user_id: Optional[str] = None
    metadata_json: Optional[str] = None


# ── Responses ──────────────────────────────────────────

class PresignUploadResponse(BaseModel):
    file_id: str
    upload_url: str
    s3_key: str


class PresignDownloadResponse(BaseModel):
    download_url: str
    file_id: str
    file_type: str


class FileResponse(BaseModel):
    id: str
    session_id: str
    user_id: Optional[str]
    category: str
    file_type: str
    s3_key: str
    size_bytes: Optional[int]
    mime_type: Optional[str]
    original_filename: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class SaveCropsResponse(BaseModel):
    session_id: str
    frame_index: int
    detection_index: int
    file_ids: dict[str, str]   # {"face": file_id, "eyes": file_id, ...}


class CleanupResponse(BaseModel):
    deleted_count: int


class HealthResponse(BaseModel):
    status: str
    s3_connected: bool
    db_connected: bool