"""
FileRecord — one row per file stored in MinIO.

Pre-created on presign-upload (before bytes arrive) so a row always
exists for any s3_key we hand out. Cleanup jobs can later find orphans
where the upload never completed (no corresponding object in MinIO).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, Enum, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.Entities.Base import Base


class FileRecord(Base):
    __tablename__ = "files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    category = Column(
        Enum("source", "burned", "crop", name="file_category"),
        nullable=False,
    )
    file_type = Column(Text, nullable=False)         # video, image, etc.
    s3_key = Column(Text, nullable=False, unique=True)
    size_bytes = Column(BigInteger, nullable=True)
    mime_type = Column(Text, nullable=True)
    original_filename = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict)

    __table_args__ = (
        Index("idx_files_session_category", "session_id", "category"),
        Index("idx_files_category_filetype", "category", "file_type"),
    )