"""
Storage Service configuration — loaded from environment variables.
"""
import os

# ── S3 / MinIO ─────────────────────────────────────────
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadmin")
S3_BUCKET = os.getenv("S3_BUCKET", "emotion-recognition")
S3_REGION = os.getenv("S3_REGION", "us-east-1")

# ── PostgreSQL ─────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/storage_db",
)

# ── Kafka (event publishing) ──────────────────────────
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC_STORAGE_EVENTS = os.getenv("TOPIC_STORAGE_EVENTS", "storage_events")

# ── Pre-signed URLs ────────────────────────────────────
PRESIGN_UPLOAD_EXPIRY = int(os.getenv("PRESIGN_UPLOAD_EXPIRY", "3600"))      # 1 hour
PRESIGN_DOWNLOAD_EXPIRY = int(os.getenv("PRESIGN_DOWNLOAD_EXPIRY", "3600"))  # 1 hour

# ── Cleanup ────────────────────────────────────────────
CLEANUP_EXPIRY_DAYS = int(os.getenv("CLEANUP_EXPIRY_DAYS", "7"))