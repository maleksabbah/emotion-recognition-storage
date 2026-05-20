"""
FileService — presign, save, list.

Each method is one named operation. S3 + DB writes paired so a row
always exists for any s3_key we hand out / store.
"""
from __future__ import annotations

import base64
import uuid
from typing import Optional

from app.Dtos.FileDto.FileResponse import FileResponse
from app.Dtos.FileDto.PresignDownloadRequest import PresignDownloadRequest
from app.Dtos.FileDto.PresignDownloadResponse import PresignDownloadResponse
from app.Dtos.FileDto.PresignUploadRequest import PresignUploadRequest
from app.Dtos.FileDto.PresignUploadResponse import PresignUploadResponse
from app.Dtos.FileDto.SaveCropsRequest import SaveCropsRequest
from app.Dtos.FileDto.SaveCropsResponse import SaveCropsResponse, SavedCropInfo
from app.Dtos.FileDto.SaveOutputRequest import SaveOutputRequest
from app.Dtos.FileDto.SaveOutputResponse import SaveOutputResponse
from app.Entities.FileRecord import FileRecord
from app.Exceptions import FileNotFound
from app.Repositories.FileRepository import FileRepository
from app.Repositories.S3Client import S3Client


class FileService:
    def __init__(self, files: FileRepository, s3:S3Client):
        self.files = files
        self.s3 = s3
    # ══════════════════════════════════════════
    # Presign — upload (browser → MinIO direct)
    # ══════════════════════════════════════════

    async def presign_upload(self,req: PresignUploadRequest) -> PresignUploadResponse:
        file_id = uuid.uuid4()
        s3_key = self._upload_key(req.session_id, file_id,req.original_filename)

        record = FileRecord(
            id=file_id,
            session_id=uuid.UUID(req.session_id),
            user_id=uuid.UUID(req.user_id) if req.user_id else None,
            category="source",
            file_type=req.file_type,
            s3_key=s3_key,
            mime_type=req.mime_type,
            original_filename=req.original_filename,

        )
        await self.files.create(record)

        upload_url = await self.s3.presign_put(s3_key,req.mime_type)
        return PresignUploadResponse(
            file_id=str(file_id),
            upload_url=upload_url,
            s3_key=s3_key,
        )

    # ══════════════════════════════════════════
    # Presign — download (browser ← MinIO direct)
    # ══════════════════════════════════════════

    async def presign_download(self,req: PresignDownloadRequest) -> PresignDownloadResponse:
        record = await self.files.find_by_id(req.file_id)
        if not record:
            raise FileNotFound()

        download_url = await self.s3.presign_get(record.s3_key)
        return PresignDownloadResponse(
            file_id=str(record.id),
            download_url=download_url,
            file_type=record.file_type,
            s3_key=record.s3_key,
        )

    # ══════════════════════════════════════════
    # Save crops (orchestrator → storage)
    # ══════════════════════════════════════════

    async def save_crops(self,req: SaveCropsRequest) -> SaveCropsResponse:
        records: list[FileRecord] = []
        result_map: dict[str,SavedCropInfo] = {}

        for region,b64 in req.crops.items():
            data = base64.b64decode(b64)
            file_id = uuid.uuid4()
            s3_key = self._crop_key(
                req.session_id,req.frame_index,req.detection_index,region,file_id)

            await self.s3.put_object(s3_key,data,"image/jpeg")
            records.append(FileRecord(
                id=file_id,
                session_id=uuid.UUID(req.session_id),
                category="crop",
                file_type=region,
                s3_key=s3_key,
                size_bytes=len(data),
                mime_type="image/jpeg",
            ))
            result_map[region] = SavedCropInfo(file_id=str(file_id), s3_key=s3_key)

        await self.files.create_many(records)
        return SaveCropsResponse(file_ids=result_map)
    # ══════════════════════════════════════════
    # Save output (burner → storage)
    # ══════════════════════════════════════════

    async def save_output(self,req: SaveOutputRequest) -> SaveOutputResponse:
        data = base64.b64decode(req.data)
        file_id = uuid.uuid4()
        s3_key = self._output_key(req.session_id,file_id,req.mime_type)

        await self.s3.put_object(s3_key,data,req.mime_type)

        record = FileRecord(
            id=file_id,
            session_id=uuid.UUID(req.session_id),
            category="burned",
            file_type=req.file_type,
            s3_key=s3_key,
            size_bytes=len(data),
            mime_type=req.mime_type,

        )
        await self.files.create(record)
        return SaveOutputResponse(file_id=str(file_id), s3_key=s3_key)
    # ══════════════════════════════════════════
    # List
    # ══════════════════════════════════════════
    async def list_files(
            self,
            session_id: Optional[str] = None,
            user_id: Optional[str] = None,
            category: Optional[str] = None,
            file_type: Optional[str] = None,

    )-> list[FileRecord]:
        rows = await self.files.list_files(
            session_id=session_id,
            user_id=user_id,
            category=category,
            file_type=file_type,
        )
        return [self._to_response(r) for r in rows]

    # ══════════════════════════════════════════
    # Key builders
    # ══════════════════════════════════════════
    @staticmethod
    def _upload_key(session_id: str, file_id: uuid.UUID, filename:Optional[str]) -> str:
        suffix = filename or "upload"
        return f"sessions/{session_id}/source/{file_id}_{suffix}"
    @staticmethod
    def _crop_key(
        session_id: str,
        frame_index: int,
        detection_index: int,
        region: str,
        file_id: uuid.UUID,
    ) -> str:
        return (
            f"sessions/{session_id}/crops/frame_{frame_index}/"
            f"det_{detection_index}/{region}_{file_id}.jpg"
        )

    @staticmethod
    def _output_key(session_id: str, file_id: uuid.UUID, mime_type: str) -> str:
        ext = "mp4" if "video" in mime_type else "jpg"
        return f"sessions/{session_id}/burned/{file_id}.{ext}"

    @staticmethod
    def _to_response(r: FileRecord) -> FileResponse:
        return FileResponse.model_validate({
            "id": str(r.id),
            "session_id": str(r.session_id),
            "user_id": str(r.user_id) if r.user_id else None,
            "category": r.category,
            "file_type": r.file_type,
            "s3_key": r.s3_key,
            "size_bytes": r.size_bytes,
            "mime_type": r.mime_type,
            "original_filename": r.original_filename,
            "created_at": r.created_at,
            "expires_at": r.expires_at,
        })































































































































































































