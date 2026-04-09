"""
ORM Models — storage_db tables.

files: tracks every file stored in S3.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, BigInteger, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.Database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


class FileRecord(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    # What kind of file
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # S3 location
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)

    # Metadata
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Extra metadata as JSON string
    metadata_json: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    __table_args__ = (
        Index("ix_files_category_type", "category", "file_type"),
        Index("ix_files_session_category", "session_id", "category"),
    )

    def __repr__(self) -> str:
        return f"<FileRecord id={self.id} type={self.file_type} s3_key={self.s3_key}>"