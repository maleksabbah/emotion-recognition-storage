"""
FileRepository — DB access for the files table.

Services call these; SQLAlchemy never leaks past this class.
"""
from __future__ import annotations

import uuid
from typing import Iterable, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.Entities.FileRecord import FileRecord


class FileRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_id(self, file_id: str | uuid.UUID) -> Optional[FileRecord]:
        uid = _as_uuid(file_id)
        result = await self.db.execute(select(FileRecord).where(FileRecord.id == uid))
        return result.scalar_one_or_none()

    async def list_files(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        category: Optional[str] = None,
        file_type: Optional[str] = None,
    ) -> list[FileRecord]:
        stmt = select(FileRecord)
        if session_id is not None:
            stmt = stmt.where(FileRecord.session_id == _as_uuid(session_id))
        if user_id is not None:
            stmt = stmt.where(FileRecord.user_id == _as_uuid(user_id))
        if category is not None:
            stmt = stmt.where(FileRecord.category == category)
        if file_type is not None:
            stmt = stmt.where(FileRecord.file_type == file_type)
        result = await self.db.execute(stmt.order_by(FileRecord.created_at.desc()))
        return list(result.scalars().all())

    async def find_source_for_session(self, session_id: str) -> Optional[FileRecord]:
        """Latest category='source' row for a session (one per presign)."""
        result = await self.db.execute(
            select(FileRecord)
            .where(
                FileRecord.session_id == _as_uuid(session_id),
                FileRecord.category == "source",
            )
            .order_by(FileRecord.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_size(self, file_id: str | uuid.UUID, size_bytes: int) -> None:
        await self.db.execute(
            update(FileRecord)
            .where(FileRecord.id == _as_uuid(file_id))
            .values(size_bytes=size_bytes)
        )

    async def delete_by_ids(self, file_ids: Iterable[uuid.UUID]) -> None:
        ids = list(file_ids)
        if not ids:
            return
        await self.db.execute(delete(FileRecord).where(FileRecord.id.in_(ids)))

    async def create(self, record: FileRecord) -> FileRecord:
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def create_many(self, records: Iterable[FileRecord]) -> None:
        self.db.add_all(list(records))
        await self.db.flush()


def _as_uuid(value: str | uuid.UUID) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))