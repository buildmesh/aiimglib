# AI Image Library – Design (2025-11-14)

## 1. Goals & Constraints
- Provide a local-only web experience for browsing hundreds of AI-generated images with rich metadata (prompt, model, rating, date, tags).
- Support adding new images and editing existing metadata through the browser; no manual JSON edits or file copying.
- Enable lightweight metadata search/filtering (text, tags, rating, date) that feels instant for a few hundred entries.
- Preference for Python backend (FastAPI), minimal dependencies, and simple deployment (single process via Uvicorn).
- Continue storing image binaries on disk, but migrate metadata from JSON to SQLite for transactional safety.

## 2. High-Level Architecture
- **FastAPI backend** owns REST APIs, static-file serving, and a small HTML/JS frontend bundle. Runs as one service (`uvicorn app.main:app`).
- **SQLite + SQLModel** persist metadata. Backend loads a SQLModel engine at startup, runs `create_all`, and exposes sessions via dependency injection.
- **Images directory** (`images/`) remains the source of truth for binaries; FastAPI mounts it through `StaticFiles` at `/images`.
- **Frontend** is a lightweight SPA (could be vanilla JS + HTMX/Alpine or a small Vite build) compiled into `static/` and served at `/`. It hits JSON APIs under `/api/*`.
- Optional JSON-to-DB migration script runs once to import the historical metadata and map tags/relationships.

## 3. Data & Storage Schema
Use SQLModel models that double as Pydantic schemas:
- `Image`: `id` (UUID string PK), `file_name`, `prompt_text` (TEXT), `prompt_meta` (JSON to capture the array form for edit provenance), `ai_model`, `notes`, `rating` (`INT CHECK 0-5`), `captured_at` (ISO 8601 string), `created_at`, `updated_at`.
- `Tag`: `id` (auto int PK), `name` (unique, indexed, lowercased for deduping).
- `ImageTagLink`: association table with `image_id` FK + `tag_id` FK.
Indexes: `Image.prompt_text` (for LIKE searches), `Image.rating`, `Image.captured_at`, `Tag.name`. Use SQLModel relationship helpers for eager loading of tags. All mutations execute inside a DB transaction to keep metadata consistent with filesystem writes.

## 4. API Surface (all JSON unless noted)
- `GET /` – serves gallery HTML.
- `GET /images/{file_name}` – static image serving via `StaticFiles`.
- `GET /api/images` – list with filters: `q` (text search across prompt/notes/ai_model), `tags` (comma list, AND semantics), `rating_min`, `rating_max`, `date_from`, `date_to`, pagination (`page`, `page_size`). Returns `{items: [...], total: n}` with embedded tag arrays.
- `GET /api/images/{id}` – detail view including raw `prompt_meta` and filesystem URL.
- `POST /api/images` (multipart) – accepts `image_file` + JSON metadata fields; generates UUID, saves file, inserts DB rows, returns created record.
- `PUT /api/images/{id}` – update metadata only; uses JSON body with partial fields.
- `POST /api/images/{id}/file` – optional endpoint to replace the image binary (validates extension, overwrites file, updates filename if needed).
- `DELETE /api/images/{id}` – removes DB record and image file.
- `GET /api/tags` – list all tags with usage counts for the frontend tag picker.
All endpoints share standard FastAPI error handling; validation errors return 422 with field details.

## 5. Frontend Experience
- Entry page shows header (search inputs + "Add Image" button) and a responsive gallery grid.
- Each tile renders thumbnail (served from `/images/...`), prompt snippet, ai_model, rating stars, tags chips, date.
- Search controls: free-text input, multi-select tag dropdown (with typeahead preloaded from `/api/tags`), rating slider, date range picker, and sort dropdown (newest, highest rating).
- Tiles support click-to-open modal displaying full-size image plus metadata form (fields editable inline). Save button triggers `PUT /api/images/{id}`; optimistic UI updates list.
- Floating “Add Image” button opens modal with upload form: file picker, prompt (textarea or JSON-aware editor), AI model dropdown/text, notes, rating slider, date picker, tags multi-select allowing creation of new tags. On submit, send multipart to `POST /api/images` and refresh gallery.
- Pagination/infinite scroll fetches additional pages via `GET /api/images?page=n` to avoid loading everything at once.

## 6. Upload & Edit Workflow Safety
1. User selects image + enters metadata.
2. Backend stores upload to temp path, validates metadata (Pydantic model), generates UUID filename, moves file into `images/`, and within a DB transaction inserts/updates `Image` row plus tag links. If any step fails, temp file is removed and DB transaction rolled back.
3. For edits, backend updates metadata fields and tag associations (create missing tags, delete unused links) within a transaction.
4. Deletes remove the DB row first, then unlink the image file; errors on file removal are logged but do not reinsert DB data.

## 7. Search & Filtering Behavior
- Text search uses SQL `LIKE` against `prompt_text`, `notes`, and `ai_model` (case-insensitive). For future upgrades we can add FTS5 virtual tables.
- Tag filtering uses an `INNER JOIN` with `ImageTagLink` and `Tag`, grouping by image and requiring matches for all requested tags.
- Rating/date filters translate to `BETWEEN` clauses on `rating` and `captured_at`.
- Results sorted by `captured_at DESC` by default, with optional `rating DESC` or `created_at DESC`.

## 8. Deployment & Operations
- Local run via `uvicorn app.main:app --reload` (Poetry or pipenv). All assets live inside the repo, so distribution is copying the folder.
- Backups: copy `app.db` and `images/` directories. Optionally expose a `/api/export` endpoint to dump JSON for external tools.
- Logging: use FastAPI/UVicorn default logging plus structured logs around uploads to track new entries.
- Authentication is omitted for local use; add HTTP Basic or auth proxy later if needed.

## 9. Future Enhancements & Risks
- **FTS search**: migrate prompts/notes to SQLite FTS for faster substring queries if catalog grows.
- **Versioned metadata**: track history of edits per image.
- **Bulk import**: CLI to ingest entire folders automatically and prompt for missing metadata.
- **Auth & sharing**: if exposed beyond localhost, add auth + rate limiting.
- **File consistency**: consider storing hash/size to detect drift between DB and filesystem.

This design keeps implementation tight while supporting future growth, leveraging FastAPI + SQLModel for a reliable local gallery and upload manager.
