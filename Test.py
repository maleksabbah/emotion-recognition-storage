"""
Storage Service Test Suite
Run: pytest Test.py -v -o asyncio_mode=auto -o python_files=Test.py -o python_classes=Test
"""
from __future__ import annotations

import base64
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.Database import Base, get_db
from app.ORM_Models import FileRecord
from app.S3 import S3Client
from app.Routes import get_s3
import app.Events as events_module


# ══════════════════════════════════════════════
# Test database setup (async SQLite in-memory)
# ══════════════════════════════════════════════

TEST_DB_URL = "sqlite+aiosqlite:///./test_storage.db"
test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with test_session_factory() as session:
        yield session


# ══════════════════════════════════════════════
# Mock S3 client
# ══════════════════════════════════════════════

class MockS3Client:
    """In-memory S3 mock — stores objects in a dict."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def ensure_bucket(self):
        pass

    def upload_bytes(self, s3_key: str, data: bytes, content_type: str = "") -> int:
        self.objects[s3_key] = data
        return len(data)

    def generate_presigned_upload(self, s3_key: str, content_type: str = "") -> str:
        return f"https://mock-s3/upload/{s3_key}"

    def generate_presigned_download(self, s3_key: str) -> str:
        return f"https://mock-s3/download/{s3_key}"

    def delete_object(self, s3_key: str) -> None:
        self.objects.pop(s3_key, None)

    def delete_objects(self, s3_keys: list[str]) -> int:
        count = 0
        for key in s3_keys:
            if key in self.objects:
                del self.objects[key]
                count += 1
        return count

    def check_connection(self) -> bool:
        return True


# ══════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════

@pytest.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
def disable_kafka_events():
    """Disable Kafka events during tests — no real Kafka connection."""
    events_module._producer = None
    yield
    events_module._producer = None


@pytest.fixture
def mock_s3():
    return MockS3Client()


@pytest.fixture
async def client(mock_s3):
    from app.main import app
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_s3] = lambda: mock_s3
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_crops_b64():
    """Base64 encoded dummy JPEG crops."""
    import cv2
    import numpy as np
    crops = {}
    for name, size in [("face", 224), ("eyes", 64), ("mouth", 64),
                        ("cheeks", 64), ("forehead", 64)]:
        img = np.zeros((size, size, 3), dtype=np.uint8)
        _, buf = cv2.imencode(".jpg", img)
        crops[name] = base64.b64encode(buf.tobytes()).decode("utf-8")
    return crops


# ══════════════════════════════════════════════
# Presign upload tests
# ══════════════════════════════════════════════

class TestPresignUpload:
    @pytest.mark.asyncio
    async def test_presign_upload_returns_url(self, client):
        resp = await client.post("/internal/presign/upload", json={
            "session_id": "sess-1",
            "file_type": "video_upload",
            "mime_type": "video/mp4",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "upload_url" in data
        assert "file_id" in data
        assert "s3_key" in data
        assert data["s3_key"].startswith("uploads/sess-1/")

    @pytest.mark.asyncio
    async def test_presign_upload_registers_in_db(self, client):
        resp = await client.post("/internal/presign/upload", json={
            "session_id": "sess-1",
            "file_type": "video_upload",
            "mime_type": "video/mp4",
            "original_filename": "my_video.mp4",
            "user_id": "user-1",
        })
        file_id = resp.json()["file_id"]

        # Fetch the file
        resp2 = await client.get(f"/internal/files/{file_id}")
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["session_id"] == "sess-1"
        assert data["file_type"] == "video_upload"
        assert data["category"] == "input"
        assert data["user_id"] == "user-1"
        assert data["original_filename"] == "my_video.mp4"

    @pytest.mark.asyncio
    async def test_presign_upload_extension_mapping(self, client):
        resp = await client.post("/internal/presign/upload", json={
            "session_id": "sess-1",
            "file_type": "image_upload",
            "mime_type": "image/jpeg",
        })
        assert resp.json()["s3_key"].endswith(".jpg")


# ══════════════════════════════════════════════
# Presign download tests
# ══════════════════════════════════════════════

class TestPresignDownload:
    @pytest.mark.asyncio
    async def test_presign_download_returns_url(self, client):
        # First create a file
        resp = await client.post("/internal/presign/upload", json={
            "session_id": "sess-1",
            "file_type": "video_upload",
            "mime_type": "video/mp4",
        })
        file_id = resp.json()["file_id"]

        # Get download URL
        resp2 = await client.post("/internal/presign/download", json={
            "file_id": file_id,
        })
        assert resp2.status_code == 200
        data = resp2.json()
        assert "download_url" in data
        assert data["file_id"] == file_id

    @pytest.mark.asyncio
    async def test_presign_download_not_found(self, client):
        resp = await client.post("/internal/presign/download", json={
            "file_id": "nonexistent",
        })
        assert resp.status_code == 404


# ══════════════════════════════════════════════
# Save crops tests
# ══════════════════════════════════════════════

class TestSaveCrops:
    @pytest.mark.asyncio
    async def test_save_crops_uploads_to_s3(self, client, mock_s3, sample_crops_b64):
        resp = await client.post("/internal/save-crops", json={
            "session_id": "sess-1",
            "frame_index": 0,
            "detection_index": 0,
            "crops": sample_crops_b64,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["file_ids"]) == 5
        assert set(data["file_ids"].keys()) == {"face", "eyes", "mouth", "cheeks", "forehead"}

        # Verify S3 has the objects
        assert len(mock_s3.objects) == 5
        for key in mock_s3.objects:
            assert key.startswith("crops/sess-1/frame_0/det_0/")

    @pytest.mark.asyncio
    async def test_save_crops_registers_in_db(self, client, sample_crops_b64):
        resp = await client.post("/internal/save-crops", json={
            "session_id": "sess-1",
            "frame_index": 0,
            "detection_index": 0,
            "crops": sample_crops_b64,
        })
        file_ids = resp.json()["file_ids"]

        # Check each crop is in the DB
        for crop_name, file_id in file_ids.items():
            resp2 = await client.get(f"/internal/files/{file_id}")
            assert resp2.status_code == 200
            data = resp2.json()
            assert data["category"] == "crop"
            assert data["file_type"] == crop_name
            assert data["mime_type"] == "image/jpeg"

    @pytest.mark.asyncio
    async def test_save_crops_metadata(self, client, sample_crops_b64):
        resp = await client.post("/internal/save-crops", json={
            "session_id": "sess-1",
            "frame_index": 5,
            "detection_index": 2,
            "crops": sample_crops_b64,
        })
        file_id = list(resp.json()["file_ids"].values())[0]

        resp2 = await client.get(f"/internal/files/{file_id}")
        data = resp2.json()
        assert data["s3_key"].startswith("crops/sess-1/frame_5/det_2/")


# ══════════════════════════════════════════════
# File queries tests
# ══════════════════════════════════════════════

class TestFileQueries:
    @pytest.mark.asyncio
    async def test_list_files_by_session(self, client, sample_crops_b64):
        # Save crops for two sessions
        await client.post("/internal/save-crops", json={
            "session_id": "sess-1", "frame_index": 0,
            "detection_index": 0, "crops": sample_crops_b64,
        })
        await client.post("/internal/save-crops", json={
            "session_id": "sess-2", "frame_index": 0,
            "detection_index": 0, "crops": sample_crops_b64,
        })

        resp = await client.get("/internal/files?session_id=sess-1")
        assert resp.status_code == 200
        files = resp.json()
        assert len(files) == 5
        assert all(f["session_id"] == "sess-1" for f in files)

    @pytest.mark.asyncio
    async def test_list_files_by_category(self, client, sample_crops_b64):
        # Create a crop and an upload
        await client.post("/internal/save-crops", json={
            "session_id": "sess-1", "frame_index": 0,
            "detection_index": 0, "crops": sample_crops_b64,
        })
        await client.post("/internal/presign/upload", json={
            "session_id": "sess-1", "file_type": "video_upload",
            "mime_type": "video/mp4",
        })

        resp = await client.get("/internal/files?category=crop")
        assert len(resp.json()) == 5

        resp2 = await client.get("/internal/files?category=input")
        assert len(resp2.json()) == 1

    @pytest.mark.asyncio
    async def test_get_file_not_found(self, client):
        resp = await client.get("/internal/files/nonexistent")
        assert resp.status_code == 404


# ══════════════════════════════════════════════
# File deletion tests
# ══════════════════════════════════════════════

class TestFileDeletion:
    @pytest.mark.asyncio
    async def test_delete_file(self, client, mock_s3, sample_crops_b64):
        resp = await client.post("/internal/save-crops", json={
            "session_id": "sess-1", "frame_index": 0,
            "detection_index": 0, "crops": sample_crops_b64,
        })
        file_id = list(resp.json()["file_ids"].values())[0]

        # Delete
        resp2 = await client.delete(f"/internal/files/{file_id}")
        assert resp2.status_code == 200

        # Verify gone from DB
        resp3 = await client.get(f"/internal/files/{file_id}")
        assert resp3.status_code == 404

        # Verify S3 has 4 objects (1 deleted)
        assert len(mock_s3.objects) == 4

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client):
        resp = await client.delete("/internal/files/nonexistent")
        assert resp.status_code == 404


# ══════════════════════════════════════════════
# Cleanup tests
# ══════════════════════════════════════════════

class TestCleanup:
    @pytest.mark.asyncio
    async def test_cleanup_expired_files(self, client, mock_s3):
        # Manually insert an expired file
        async with test_session_factory() as db:
            record = FileRecord(
                session_id="sess-old",
                category="crop",
                file_type="face",
                s3_key="crops/old/face.jpg",
                expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            )
            db.add(record)
            await db.commit()
            file_id = record.id

        mock_s3.objects["crops/old/face.jpg"] = b"data"

        resp = await client.post("/internal/cleanup")
        assert resp.status_code == 200
        assert resp.json()["deleted_count"] == 1
        assert "crops/old/face.jpg" not in mock_s3.objects

    @pytest.mark.asyncio
    async def test_cleanup_skips_non_expired(self, client, mock_s3):
        # Insert a file that expires in the future
        async with test_session_factory() as db:
            record = FileRecord(
                session_id="sess-new",
                category="crop",
                file_type="face",
                s3_key="crops/new/face.jpg",
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            )
            db.add(record)
            await db.commit()

        mock_s3.objects["crops/new/face.jpg"] = b"data"

        resp = await client.post("/internal/cleanup")
        assert resp.json()["deleted_count"] == 0
        assert "crops/new/face.jpg" in mock_s3.objects

    @pytest.mark.asyncio
    async def test_cleanup_no_expired(self, client):
        resp = await client.post("/internal/cleanup")
        assert resp.json()["deleted_count"] == 0


# ══════════════════════════════════════════════
# Register file tests
# ══════════════════════════════════════════════

class TestRegisterFile:
    @pytest.mark.asyncio
    async def test_register_file(self, client):
        resp = await client.post("/internal/register", json={
            "session_id": "sess-1",
            "category": "output",
            "file_type": "annotated_video",
            "s3_key": "outputs/sess-1/annotated.mp4",
            "size_bytes": 1024000,
            "mime_type": "video/mp4",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "output"
        assert data["file_type"] == "annotated_video"
        assert data["s3_key"] == "outputs/sess-1/annotated.mp4"


# ══════════════════════════════════════════════
# Health check tests
# ══════════════════════════════════════════════

class TestHealth:
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["s3_connected"] is True
        assert data["db_connected"] is True


# ══════════════════════════════════════════════
# Kafka event tests
# ══════════════════════════════════════════════

class TestEvents:
    @pytest.mark.asyncio
    async def test_publish_event_skips_when_no_producer(self):
        from app.Events import publish_event
        events_module._producer = None
        await publish_event("test_event", {"key": "value"})  # Should not raise

    @pytest.mark.asyncio
    async def test_publish_event_with_producer(self):
        from app.Events import publish_event
        mock_prod = AsyncMock()
        mock_prod.send_and_wait = AsyncMock()
        events_module._producer = mock_prod
        await publish_event("test_event", {"key": "value"})
        mock_prod.send_and_wait.assert_called_once()
        call_val = mock_prod.send_and_wait.call_args[1]["value"]
        assert call_val["event_type"] == "test_event"
        assert call_val["key"] == "value"
        assert "timestamp" in call_val
        events_module._producer = None

    @pytest.mark.asyncio
    async def test_publish_event_survives_kafka_failure(self):
        from app.Events import publish_event
        mock_prod = AsyncMock()
        mock_prod.send_and_wait = AsyncMock(side_effect=Exception("Kafka down"))
        events_module._producer = mock_prod
        await publish_event("test_event", {"key": "value"})  # Should not raise
        events_module._producer = None

    @pytest.mark.asyncio
    async def test_emit_crops_saved(self):
        from app.Events import emit_crops_saved
        mock_prod = AsyncMock()
        mock_prod.send_and_wait = AsyncMock()
        events_module._producer = mock_prod
        await emit_crops_saved("sess-1", 0, 0, {"face": "f1"})
        call_val = mock_prod.send_and_wait.call_args[1]["value"]
        assert call_val["event_type"] == "crops_saved"
        assert call_val["session_id"] == "sess-1"
        assert call_val["file_ids"] == {"face": "f1"}
        events_module._producer = None

    @pytest.mark.asyncio
    async def test_emit_file_deleted(self):
        from app.Events import emit_file_deleted
        mock_prod = AsyncMock()
        mock_prod.send_and_wait = AsyncMock()
        events_module._producer = mock_prod
        await emit_file_deleted("file-1", "crops/test/face.jpg")
        call_val = mock_prod.send_and_wait.call_args[1]["value"]
        assert call_val["event_type"] == "file_deleted"
        assert call_val["file_id"] == "file-1"
        events_module._producer = None