# AI Image Library – Design (2025-11-17)

> **Status (2025-11-17):** v1.0 is live. This revision captures the v1.1 scope (video ingestion, richer prompt references, decimal ratings). Continue editing only the `frontend/` sources and regenerate the Vite bundle instead of touching files under `app/static/`.

## 1. Goals & Constraints
- Provide a local-only web experience for browsing hundreds of AI-generated images with rich metadata (prompt, model, rating, date, tags).
- Support adding new images *and videos* (with thumbnails) plus editing metadata through the browser; no manual JSON edits or file copying.
- Enable lightweight metadata search/filtering (text, tags, rating, date) that feels instant for a few hundred entries.
- Ratings now accept tenths (0.0–5.0); search filters and UI controls must support decimal values.
- Preference for Python backend (FastAPI), minimal dependencies, and simple deployment (single process via Uvicorn).
- Continue storing binaries on disk (images + videos + thumbnails) while keeping metadata in SQLite for transactional safety.
- Prompt metadata is formalized as either a plain string or an array of zero or more reference objects `{ "id": "<uuid>" }` followed by the prompt text string. This enables chained edits and UI conveniences.

## 2. High-Level Architecture
- **FastAPI backend** owns REST APIs, static-file serving, and a small HTML/JS frontend bundle. Runs as one service (`uvicorn app.main:app`).
- **Containerized runtime** packages the FastAPI app, uv-managed virtual environment, and frontend bundle inside a single Docker image so the whole stack launches via `docker compose up`.
- **SQLite + SQLModel** persist metadata. Backend loads a SQLModel engine at startup, runs `create_all`, and exposes sessions via dependency injection.
- **Images directory** (`images/`) remains the source of truth for binaries; FastAPI mounts it through `StaticFiles` at `/images`.
- **Frontend** is a lightweight SPA (could be vanilla JS + HTMX/Alpine or a small Vite build) compiled into `static/` and served at `/`. It hits JSON APIs under `/api/*`.
- Optional JSON-to-DB migration script runs once to import the historical metadata and map tags/relationships.

## 3. Data & Storage Schema
Use SQLModel models that double as Pydantic schemas:
- `Image`: `id` (UUID PK), `media_type` (`Enum["image","video"]`), `file_name` (primary binary path), `thumbnail_file` (nullable string, required for videos, optional overrides for images), `prompt_text`, `prompt_meta` (string or array per spec), `ai_model`, `notes`, `rating` (`DECIMAL(2,1)` or REAL with validation 0.0–5.0), `captured_at`, `created_at`, `updated_at`.
- `Tag`: `id` (auto int PK), `name` (unique, indexed, lowercased for deduping).
- `ImageTagLink`: association table with `image_id` FK + `tag_id` FK.
Indexes: `Image.media_type`, `Image.prompt_text`, `Image.rating`, `Image.captured_at`, `Tag.name`. Use SQLModel relationship helpers for eager loading of tags. All mutations execute inside a DB transaction to keep metadata consistent with filesystem writes.
Prompt metadata validation: when `prompt_meta` is a list, every element except the last must be an object containing only `id`; the final element must be the textual prompt string. This enables the UI to display reference thumbnails and link to upstream entries.

## 4. API Surface (all JSON unless noted)
- `GET /` – serves gallery HTML.
- `GET /images/{file_name}` – static image serving via `StaticFiles`.
- `GET /api/images` – list with filters: `q`, `tags`, `media_type` (optional), `rating_min`, `rating_max`, `date_from`, `date_to`, pagination (`page`, `page_size`). Ratings accept decimals.
- `GET /api/images/{id}` – detail view including raw `prompt_meta`, resolved references, media URLs for both `file_name` and `thumbnail_file`.
- `POST /api/images` (multipart) – accepts `media_file` (required), `thumbnail_file` (optional but mandatory when `media_type=video`), plus JSON fields (`media_type`, `prompt_text`, `prompt_meta`, `ai_model`, `notes`, `rating`, `captured_at`, `tags`). Generates UUID, saves binaries, writes DB row, returns created record. Breaking change: legacy `image_file` is no longer accepted.
- `PUT /api/images/{id}` – update metadata only; uses JSON body with partial fields.
- `POST /api/images/{id}/file` – replace primary binary; respects `media_type` validation (videos must use allowed extensions/MIME types). Separate endpoint (or same) for `thumbnail_file` replacement.
- `DELETE /api/images/{id}` – removes DB record and image file.
- `GET /api/tags` – list all tags with usage counts for the frontend tag picker.
All endpoints share standard FastAPI error handling; validation errors return 422 with field details.

## 5. Frontend Experience
- Entry page shows header (search inputs + "Add Media" button) and responsive gallery grid. Cards display either `<img>` thumbnails or `<video>` overlays depending on `media_type`.
- Search controls: free-text input, collapsible tag picker, decimal rating filters (`step=0.1`), date range picker, optional media-type filter. “Clear filters” resets all inputs.
- Tiles now open a richer detail modal: inline HTML5 video playback for `media_type=video`, image zoom for images, metadata, rating, and list of referenced sources. Source references display thumbnails; clicking them navigates to that record’s detail modal.
- Upload modal lets users choose media type (image/video), upload `media_file`, optionally `thumbnail_file` (videos require one). Prompt editor includes a “Add reference” gallery picker so users can search/select existing assets; the thumbnail field auto-prefills with the first referenced asset but remains editable. Rating input uses a decimal-capable control.
- Edit modal mirrors upload modal (including reference picker and decimal rating).
- Pagination/infinite scroll fetches additional pages via `GET /api/images?page=n` to avoid loading everything at once.
- Source-of-truth frontend code lives under `frontend/`; the production bundle is generated into `app/static/` via `npm run build`. Built assets must never be edited manually—always change `frontend/` files and regenerate the bundle.

## 6. Upload & Edit Workflow Safety
1. User selects media (image or video) and optional thumbnail, enters metadata (prompt text, references, ai_model, notes, decimal rating, captured_at, tags).
2. Backend stores uploads to temp paths, validates metadata (including prompt reference structure, media type, required thumbnail for videos), generates UUID filenames, moves files into `images/`, and within a DB transaction inserts/updates `Image` row plus tag links. If any step fails, temp files are removed and the DB transaction is rolled back.
3. For edits, backend updates metadata fields, prompt references, thumbnail, and tag associations within a transaction.
4. Deletes remove the DB row first, then unlink both `file_name` and `thumbnail_file`; filesystem errors are logged but do not resurrect the DB row.

## 7. Search & Filtering Behavior
- Text search uses SQL `LIKE` against `prompt_text`, `notes`, and `ai_model`. We may later consolidate into FTS5.
- Tag filtering uses `INNER JOIN` with `ImageTagLink` and `Tag`, grouping by image and requiring matches for all requested tags.
- Rating filters now accept decimals; SQL comparisons use `>=`/`<=` on REAL/NUMERIC columns.
- Optional media-type filter limits results to images or videos. Date filters remain `BETWEEN`.
- Results sorted by `captured_at DESC` by default, with optional `rating DESC` or `created_at DESC`.

## 8. Deployment & Operations
- Local run via `docker compose up --build`, which builds the container (installing Python deps through `uv pip install` inside the image) and exposes FastAPI on port 8000. For quick iteration outside the container, developers can still run `uv run uvicorn app.main:app --reload`.
- Backups: copy `app.db` and `images/` directories. Optionally expose a `/api/export` endpoint to dump JSON for external tools.
- Logging: use FastAPI/UVicorn default logging plus structured logs around uploads to track new entries.
- Authentication is omitted for local use; add HTTP Basic or auth proxy later if needed.
- Dependency management standardizes on [uv](https://github.com/astral-sh/uv), so CI/CD and developers share the same locked dependency graph via `uv.lock`. Docker builds run `uv sync --frozen` for reproducibility.
- Video support requires no additional codecs in-app because we rely on user-provided thumbnails and browser playback; ffmpeg is not bundled.

## 9. Future Enhancements & Risks
- **FTS search**: migrate prompts/notes to SQLite FTS for faster substring queries if catalog grows.
- **Versioned metadata**: track history of edits per image.
- **Bulk import**: CLI to ingest entire folders automatically and prompt for missing metadata.
- **Auth & sharing**: if exposed beyond localhost, add auth + rate limiting.
- **File consistency**: consider storing hash/size to detect drift between DB and filesystem.
- **Reference fan-out**: deep chains of prompt references could cause multiple fetches in the UI; consider caching or batching requests if the chains grow.

This design keeps implementation tight while supporting future growth, leveraging FastAPI + SQLModel for a reliable local gallery and upload manager.
