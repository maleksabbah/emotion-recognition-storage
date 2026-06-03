# EmotionRecognitionStorage

Internal file service for the Mntis platform. Owns the `storage_db`
(file registry) and brokers all access to MinIO: presigned upload
URLs, presigned download URLs, and metadata for every artifact the
pipeline produces (source images, region crops, burned images).

Built with FastAPI + aioboto3. Not exposed publicly — only other
services (and the gateway acting on behalf of users) call it.

## Architecture

The service follows a clean, layered architecture where each layer has
one responsibility and depends only on the layer beneath it:

* **Routes** — thin HTTP controllers. Internal endpoints for
  presigning uploads, presigning downloads, recording uploaded files
  (`save_file`), saving the bundle of region crops produced by the
  media worker (`save_crops`), recording the burned image, and
  listing files by session / category. They translate between HTTP
  and DTOs and call the service layer. No business logic lives here.
* **Services** — the business logic. `PresignService` builds upload
  and download URLs scoped to the right bucket + key + content type
  + expiry. `FileService` records file metadata, deduplicates by
  s3_key, and resolves listings (e.g. "every crop for this
  session"). `CropService` accepts the base64 bundle from the media
  worker, decodes and uploads each region to MinIO under the
  session's `crops/` prefix, then writes one `FileRecord` per
  region. Knows nothing about HTTP.
* **Repositories** — data access. `FileRepository` wraps the
  `files` table behind a clean interface. `S3Client` wraps aioboto3
  (presign, put_object, get_object, head_object). The service layer
  never touches SQL or raw boto3 directly.
* **Entities** — `FileRecord` ORM model — one row per object in
  MinIO, with `session_id`, `category` (`source` / `crop` /
  `burned`), `file_type` (`face` / `eyes` / `mouth` / ...),
  `s3_key`, `mime_type`, and `size_bytes`. The schema is managed
  with Alembic — migrations live under `alembic/versions/` and
  run on startup via the FastAPI `lifespan`.
* **Dtos** — the request/response shapes (`PresignUploadRequest`,
  `SaveCropsRequest`, `FileListResponse`, ...) kept separate from
  internal entities.
* **Config** — wiring: SQLAlchemy session, aioboto3 session pointed
  at the MinIO endpoint, bucket name, presign expiry.

This separation keeps the HTTP layer swappable, the business logic
testable in isolation, and the data layer free to change without
touching the rest.

Two things worth calling out: the service is the only writer to
MinIO, so every artifact path follows one convention
(`sessions/{session_id}/source|crops|burned/...`) and is paired with
a `FileRecord` row, making "list everything for this session" a
single query. And presigned URLs do the heavy lifting — large
uploads and downloads never pass through this service, only the
URL-signing step does.

Part of a multi-service system — see the [platform overview](../EmotionRecognitionDocker)
for the full architecture, pipeline flow, and the other services.
