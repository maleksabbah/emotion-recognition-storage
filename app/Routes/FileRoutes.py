"""
File routes — internal endpoints used by gateway, orchestrator, burner.

No auth: storage trusts the internal network. nginx blocks /internal/*
from the public side.

  POST /internal/presign/upload    gateway / orchestrator
  POST /internal/presign/download  gateway
  POST /internal/save-crops        orchestrator
  POST /internal/save-output       burner
  GET  /internal/files             gateway, orchestrator
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.Dtos.FileDto.FileResponse import FileResponse
from app.Dtos.FileDto.PresignDownloadRequest import PresignDownloadRequest
from app.Dtos.FileDto.PresignDownloadResponse import PresignDownloadResponse
from app.Dtos.FileDto.PresignUploadRequest import PresignUploadRequest
from app.Dtos.FileDto.PresignUploadResponse import PresignUploadResponse
from app.Dtos.FileDto.SaveCropsRequest import SaveCropsRequest
from app.Dtos.FileDto.SaveCropsResponse import SaveCropsResponse
from app.Dtos.FileDto.SaveOutputRequest import SaveOutputRequest
from app.Dtos.FileDto.SaveOutputResponse import SaveOutputResponse
from app.Services.FileService import FileService
from app.Dependencies import get_file_service

router = APIRouter(prefix="/internal", tags=["files"])


@router.post("/presign/upload", response_model=PresignUploadResponse)
async def presign_upload(
    req: PresignUploadRequest,
    files: FileService = Depends(get_file_service),
) -> PresignUploadResponse:
    return await files.presign_upload(req)


@router.post("/presign/download", response_model=PresignDownloadResponse)
async def presign_download(
    req: PresignDownloadRequest,
    files: FileService = Depends(get_file_service),
) -> PresignDownloadResponse:
    return await files.presign_download(req)


@router.post("/save-crops", response_model=SaveCropsResponse)
async def save_crops(
    req: SaveCropsRequest,
    files: FileService = Depends(get_file_service),
) -> SaveCropsResponse:
    return await files.save_crops(req)


@router.post("/save-output", response_model=SaveOutputResponse)
async def save_output(
    req: SaveOutputRequest,
    files: FileService = Depends(get_file_service),
) -> SaveOutputResponse:
    return await files.save_output(req)


@router.get("/files", response_model=list[FileResponse])
async def list_files(
    session_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    file_type: Optional[str] = Query(None),
    files: FileService = Depends(get_file_service),
) -> list[FileResponse]:
    return await files.list_files(
        session_id=session_id,
        user_id=user_id,
        category=category,
        file_type=file_type,
    )