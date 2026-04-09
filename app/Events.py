"""
Kafka event publisher — publishes storage events after each operation.

Event types:
  - file_registered: new file registered in DB (pre-signed upload created)
  - crops_saved: crops uploaded to S3 and registered
  - file_deleted: file removed from S3 and DB
  - files_cleaned: expired files bulk deleted

Events are fire-and-forget — if Kafka is down, the HTTP operation still succeeds.
The event is best-effort, not transactional with the DB write.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from aiokafka import AIOKafkaProducer

from app.Config import KAFKA_BOOTSTRAP, TOPIC_STORAGE_EVENTS

logger = logging.getLogger("storage.events")

_producer: Optional[AIOKafkaProducer] = None


async def start_producer() -> None:
    """Start the Kafka producer. Called on app startup."""
    global _producer
    try:
        _producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await _producer.start()
        logger.info("Kafka event producer started")
    except Exception as e:
        logger.warning("Kafka producer failed to start: %s — events disabled", e)
        _producer = None


async def stop_producer() -> None:
    """Stop the Kafka producer. Called on app shutdown."""
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None
        logger.info("Kafka event producer stopped")


async def publish_event(event_type: str, data: dict[str, Any]) -> None:
    """
    Publish a storage event to Kafka.
    Fire-and-forget — logs warning on failure, never raises.
    """
    if _producer is None:
        return

    event = {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **data,
    }

    try:
        await _producer.send_and_wait(TOPIC_STORAGE_EVENTS, value=event)
        logger.debug("Published event: %s", event_type)
    except Exception as e:
        logger.warning("Failed to publish event %s: %s", event_type, e)


# ── Convenience functions ──────────────────────────────

async def emit_file_registered(
    file_id: str, session_id: str, file_type: str, s3_key: str,
    user_id: str | None = None,
) -> None:
    await publish_event("file_registered", {
        "file_id": file_id,
        "session_id": session_id,
        "file_type": file_type,
        "s3_key": s3_key,
        "user_id": user_id,
    })


async def emit_crops_saved(
    session_id: str, frame_index: int, detection_index: int,
    file_ids: dict[str, str], user_id: str | None = None,
) -> None:
    await publish_event("crops_saved", {
        "session_id": session_id,
        "frame_index": frame_index,
        "detection_index": detection_index,
        "file_ids": file_ids,
        "user_id": user_id,
    })


async def emit_file_deleted(file_id: str, s3_key: str) -> None:
    await publish_event("file_deleted", {
        "file_id": file_id,
        "s3_key": s3_key,
    })


async def emit_files_cleaned(deleted_count: int, s3_keys: list[str]) -> None:
    await publish_event("files_cleaned", {
        "deleted_count": deleted_count,
        "s3_keys": s3_keys,
    })