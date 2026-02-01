# Photo Gallery Base Implementation Plan (2026-02-01)

**Goal:** Fork the AI gallery into a simplified photo gallery base with filename search, EXIF captured dates, and PWA support, while preserving the existing UI look and feel.

**Architecture:** FastAPI + SQLModel + SQLite, files on disk under `images/`, SPA frontend via Vite bundle.

## Task 1: Schema & Model Simplification

**Files:** `app/models.py`, `app/schemas.py`, `app/database.py`, `tests/test_models.py`

1. Add/update tests for the simplified `Photo` model fields (filename + captured date).
2. Remove AI-specific fields from SQLModel and schemas.
3. Ensure created/updated timestamps remain intact.
4. Run `uv run pytest tests/test_models.py -v`.
5. Commit schema changes.

## Task 2: File Handling + EXIF Parsing

**Files:** `app/services/files.py`, `app/crud.py`, `tests/test_crud.py`

1. Add tests for EXIF capture date parsing (expected, missing, malformed).
2. Ensure upload accepts common image types (jpeg, png, webp, gif, heic, heif, tiff, bmp).
3. Remove video and thumbnail handling.
4. Ensure deletes remove file + DB row.
5. Run `uv run pytest tests/test_crud.py -v`.
6. Commit file handling updates.

## Task 3: API Endpoints

**Files:** `app/api/images.py`, `app/main.py`, `app/dependencies.py`, `tests/test_images_api.py`

1. Update tests for simplified endpoints:
   - `POST /api/photos` (multipart, `photo_file`)
   - `GET /api/photos` (filename search)
   - `GET /api/photos/{id}`
   - `DELETE /api/photos/{id}`
2. Update API routes and names to match the photo-focused surface.
3. Keep static file serving at `/images/{file_name}`.
4. Run `uv run pytest tests/test_images_api.py -v`.
5. Commit API changes.

## Task 4: Frontend Prune While Preserving UI

**Files:** `frontend/index.html`, `frontend/main.js`, `frontend/styles.css`, `tests/test_frontend_smoke.py`

1. Remove AI metadata UI controls but keep layout, spacing, and typography.
2. Keep search input, rename label to indicate filename search.
3. Detail modal shows filename + captured date only.
4. Upload modal accepts only a file input.
5. Run `cd frontend && npm run test`, then `npm run build`.
6. Update smoke tests for new UI labels and buttons.
7. Commit frontend changes + rebuilt assets.

## Task 5: PWA Support

**Files:** `frontend/manifest.json`, `frontend/service-worker.js`, `frontend/index.html`, `app/static/` (rebuilt), `tests/test_frontend_smoke.py`

1. Add manifest and service worker with app shell caching.
2. Link manifest + service worker registration in `frontend/index.html`.
3. Use a network-first strategy for images.
4. Rebuild the frontend bundle.
5. Update smoke test to assert manifest link exists.
6. Commit PWA updates.

## Task 6: Documentation

**Files:** `README.md`, `docs/plans/2026-02-01-photo-gallery-base-design.md`

1. Update README with simplified feature set and PWA instructions.
2. Run full test suite:
   - `uv run pytest -v`
   - `cd frontend && npm run test`
3. Commit docs.
