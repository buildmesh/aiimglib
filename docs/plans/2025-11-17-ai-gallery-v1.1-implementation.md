# AI Gallery v1.1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the AI Image Library with video uploads + thumbnails, decimal ratings, structured prompt references, and enhanced UX (detail modal navigation + reference picker).

**Architecture:** FastAPI service + SQLite metadata (SQLModel) with binaries on disk under `images/`. Frontend remains a Vite-built SPA. Schema now includes `media_type`, `thumbnail_file`, decimal ratings, and validated prompt arrays.

**Tech Stack:** Python 3.11, FastAPI, SQLModel, Uvicorn, Pydantic, pytest + httpx, uv, Docker/Compose, Vite, Vitest.

## Execution Notes (2025-11-17)
- v1.0 code is the baseline; this plan covers the v1.1 enhancements (videos, thumbnails, decimal ratings, structured prompts).
- Both backend and frontend require changes. Use TDD: update/create tests before implementing API or schema breaking changes.
- Frontend assets are still built with Vite. Always edit files in `frontend/` and run `npm run build` to regenerate `app/static/`. Never modify `app/static/` directly.

### Task 1: Database & Schema Updates

**Files:** `app/models.py`, `app/schemas.py`, `app/database.py`, `scripts/import_legacy_json.py`, migration notes  
**Tests:** `tests/test_models.py`, `tests/test_import_legacy.py`

1. **Add failing tests** for `media_type`, `thumbnail_file`, decimal ratings, and prompt-array validation (list of `{id}` + trailing string).  
2. **Update SQLModel models** to include `media_type` Enum (default `"image"`), nullable `thumbnail_file`, `rating: float` with 0–5 validation, and prompt validator.  
3. **Adjust schemas** to expose new fields and decimal ratings in create/update/read DTOs.  
4. **Migration plan**: document SQL to add `media_type`, `thumbnail_file`, convert rating column to REAL/NUMERIC, and backfill defaults.  
5. **Importer updates** to normalize decimals, set `media_type`, `thumbnail_file`, and ensure prompt arrays follow the new contract.  
6. Run `uv run pytest tests/test_models.py tests/test_import_legacy.py -v`.  
7. Commit schema work.

### Task 2: CRUD & File Utilities

**Files:** `app/crud.py`, `app/services/files.py`, `app/services/tags.py`, `app/schemas.py`, `tests/test_crud.py`

1. **Extend tests** to cover video creation (thumbnail required), decimal rating filters, prompt references, and delete removing both binaries.  
2. **File service**: add media-type aware validation (images vs videos), helper for saving/deleting thumbnails, and safer delete logic.  
3. **CRUD changes**: enforce `thumbnail_file` for videos, store `media_type`, include filter support, cascade deletions, and guard prompt meta validation before commit.  
4. Run CRUD tests.  
5. Commit changes.

### Task 3: API Endpoints & Validation

**Files:** `app/api/images.py`, `app/api/tags.py`, `app/dependencies.py`, `app/main.py`, `app/services/files.py` (if more helpers)  
**Tests:** `tests/test_images_api.py`, `tests/test_tags_api.py`

1. **Update tests first**: adjust upload helper to send `media_file`, `thumbnail_file`, `media_type`; add decimal rating assertions and video-specific scenarios (missing thumbnail, prompt references).  
2. **Modify API**:  
   - Replace `image_file` with `media_file`. Accept `thumbnail_file` (required for videos, optional for images).  
   - Require `media_type` field; validate allowed extensions/MIME types via file service.  
   - Validate prompt arrays (list of `{id}` plus trailing string).  
   - Detail endpoint returns `media_type`, `thumbnail_file`, and resolved reference metadata (IDs, filenames, media types) for UI navigation.  
   - List endpoint gains `media_type` filter; rating min/max parse as floats.  
   - Provide thumbnail-replacement endpoint or extend existing `/file` route.  
3. Run API tests.  
4. Commit.

### Task 4: Legacy Importer Enhancements

**Files:** `scripts/import_legacy_json.py`, `README.md` (import docs), `tests/test_import_legacy.py`

1. **Add tests** for decimal rating normalization, media-type detection by extension, prompt-array conversion, and thumbnail defaults.  
2. **Implement logic** to detect `media_type`, assign `thumbnail_file` when prompt references exist, and enforce structured prompts.  
3. Update README instructions for the importer (videos, thumbnails, prompt references).  
4. Run importer tests; commit.

### Task 5: Frontend & UX

**Files:** `frontend/index.html`, `frontend/main.js`, `frontend/styles.css`, `frontend/dateUtils.js`, `frontend/referencePicker.js` (new helper), `frontend/package.json`, `frontend/vitest.config.js`, `tests/test_frontend_smoke.py`  
**Tests:** `cd frontend && npm run test`, backend smoke test

1. **Vitest coverage**: ensure `dateUtils` tests reflect filename parsing fixes; add tests for any new utilities (reference picker state, media helpers).  
2. **Upload/Edit modal**: add media-type selector, `media_file` + `thumbnail_file` inputs, decimal rating controls (`step=0.1`), and gallery-style reference picker. Auto-fill thumbnail when uploading a video referencing another asset (first reference).  
3. **Detail modal**: embed `<video>` for videos, show reference thumbnails with click-to-navigate behavior, display captured date, decimal rating, and notes.  
4. **Gallery & filters**: show video indicators, decimal ratings, collapsible tag picker with summary, clear-filters button, and optional media-type filter.  
5. **Reference navigation**: clicking a reference thumbnail opens that record’s detail modal (fetch via `/api/images/{id}`).  
6. Run Vitest, rebuild bundle (`npm run build`), ensure `app/static/` is updated.  
7. Update backend smoke test to assert new UI text (e.g., “Add Media” or references).  
8. Commit frontend + built assets.

### Task 6: Documentation & Final Verification

**Files:** `README.md`, `docs/plans/2025-11-17-ai-gallery-v1.1-design.md`, this implementation plan, optional screenshots  
**Tests:** `uv run pytest -v`, `cd frontend && npm run test`, Docker smoke test

1. **Documentation**: update README with instructions for videos, thumbnails, decimal ratings, reference picker, and importer behavior.  
2. **Full test run**: backend pytest suite, frontend Vitest, `npm run build`.  
3. **Docker validation**: `docker compose up --build`, manually upload image + video, ensure thumbnails, references, decimal filters, and detail modal navigation work.  
4. **Manual QA checklist** covering upload/edit flows, reference navigation, and filters.  
5. Commit docs + final fixes; prepare release notes if needed.

---

Plan complete and saved to `docs/plans/2025-11-17-ai-gallery-v1.1-implementation.md`. Two execution options:
1. **Subagent-Driven (this session)** – I’ll dispatch fresh subagents per task with reviews between tasks for tight feedback loops.
2. **Parallel Session (separate)** – Open a new session/worktree that uses `superpowers:executing-plans` to implement tasks in batches with checkpoints.

Which approach would you like to use?
