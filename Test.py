"""
Storage integration tests — single file.
Run from storage/ root: `pytest Test.py -v`

Requires:
  pip install asgi-lifespan
  pytest.ini with `asyncio_default_fixture_loop_scope = session`
"""
from __future__ import annotations

import base64
import os
import uuid

import httpx
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from testcontainers.minio import MinioContainer
from testcontainers.postgres import PostgresContainer


# ══════════════════════════════════════════════
# Containers
# ══════════════════════════════════════════════

@pytest.fixture(scope="session", autouse=True)
def postgres():
    with PostgresContainer("postgres:15") as pg:
        os.environ["POSTGRES_HOST"] = pg.get_container_host_ip()
        os.environ["POSTGRES_PORT"] = str(pg.get_exposed_port(5432))
        os.environ["POSTGRES_USER"] = pg.username
        os.environ["POSTGRES_PASSWORD"] = pg.password
        os.environ["STORAGE_DB"] = pg.dbname
        yield


@pytest.fixture(scope="session", autouse=True)
def minio():
    with MinioContainer() as mc:
        host = mc.get_container_host_ip()
        port = mc.get_exposed_port(9000)
        endpoint = f"http://{host}:{port}"
        os.environ["S3_INTERNAL_ENDPOINT"] = endpoint
        os.environ["S3_PUBLIC_ENDPOINT"] = endpoint
        os.environ["S3_ACCESS_KEY"] = mc.access_key
        os.environ["S3_SECRET_KEY"] = mc.secret_key
        client = mc.get_client()
        if not client.bucket_exists("emotion"):
            client.make_bucket("emotion")
        yield


# ══════════════════════════════════════════════
# App + client — session-scoped (one app, schema reset per test)
# ══════════════════════════════════════════════

@pytest_asyncio.fixture(scope="session")
async def app_and_engine():
    from app.main import app
    from app.Config.Database import engine
    from app.Entities import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with LifespanManager(app):
        yield app, engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(app_and_engine):
    app, engine = app_and_engine
    # Reset rows between tests (keep schema)
    from app.Entities import Base
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


# ══════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════

def _sid(): return str(uuid.uuid4())
def _uid(): return str(uuid.uuid4())


def _fake_jpeg() -> str:
    return base64.b64encode(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"\x00" * 100).decode()


# ══════════════════════════════════════════════
# Tests
# ══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_presign_upload_creates_file_row(client):
    r = await client.post("/internal/presign/upload", json={
        "session_id": _sid(),
        "file_type": "video",
        "mime_type": "video/mp4",
        "original_filename": "test.mp4",
        "user_id": _uid(),
    })
    assert r.status_code == 200
    body = r.json()
    assert "file_id" in body and "upload_url" in body
    assert body["s3_key"].endswith("test.mp4")


@pytest.mark.asyncio
async def test_save_crops_persists_5_rows(client):
    sid = _sid()
    crop = _fake_jpeg()
    r = await client.post("/internal/save-crops", json={
        "session_id": sid, "frame_index": 42, "detection_index": 0,
        "crops": {region: crop for region in ("face", "eyes", "mouth", "cheeks", "forehead")},
    })
    assert r.status_code == 200
    assert set(r.json()["file_ids"].keys()) == {"face", "eyes", "mouth", "cheeks", "forehead"}

    r2 = await client.get(f"/internal/files?session_id={sid}&category=crop")
    assert len(r2.json()) == 5


@pytest.mark.asyncio
async def test_save_output_persists_one_row(client):
    r = await client.post("/internal/save-output", json={
        "session_id": _sid(),
        "data": _fake_jpeg(),
        "mime_type": "video/mp4",
        "file_type": "burned",
    })
    assert r.status_code == 200
    assert r.json()["s3_key"].endswith(".mp4")


@pytest.mark.asyncio
async def test_presign_download_404_for_missing(client):
    r = await client.post("/internal/presign/download", json={"file_id": _uid()})
    assert r.status_code == 404