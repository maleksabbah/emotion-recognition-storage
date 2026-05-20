# app/Dtos/__init__.py
"""
Storage DTOs.

  FileDto/
    PresignUploadRequest/Response   POST /internal/presign/upload
    PresignDownloadRequest/Response POST /internal/presign/download
    SaveCropsRequest/Response       POST /internal/save-crops
    SaveOutputRequest/Response      POST /internal/save-output
    FileResponse                    GET  /internal/files (rows)
"""
from app.Dtos.FileDto import (
    PresignUploadRequest, PresignUploadResponse,
    PresignDownloadRequest, PresignDownloadResponse,
    SaveCropsRequest, SaveCropsResponse, SavedCropInfo,
    SaveOutputRequest, SaveOutputResponse,
    FileResponse,
)

__all__ = [
    "PresignUploadRequest", "PresignUploadResponse",
    "PresignDownloadRequest", "PresignDownloadResponse",
    "SaveCropsRequest", "SaveCropsResponse", "SavedCropInfo",
    "SaveOutputRequest", "SaveOutputResponse",
    "FileResponse",
]