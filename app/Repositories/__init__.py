"""
Storage repositories — boundary layer.

DB-backed:    FileRepository
S3-backed:    S3Client
"""
from app.Repositories.FileRepository import FileRepository
from app.Repositories.S3Client import S3Client

__all__ = ["FileRepository", "S3Client"]