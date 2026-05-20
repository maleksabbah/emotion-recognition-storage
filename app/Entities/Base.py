"""Shared SQLAlchemy declarative base for storage_db."""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass