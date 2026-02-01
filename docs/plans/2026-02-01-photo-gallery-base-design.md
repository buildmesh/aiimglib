# Photo Gallery Base – Design (2026-02-01)

> **Status (2026-02-01):** Planning for a fork that simplifies the AI gallery into a general-purpose photo gallery base. Preserve current visual design where possible.

## 1. Goals & Constraints
- Provide a local-first web app for browsing uploaded photos with minimal metadata.
- Keep the current UI structure and styling as much as possible while removing AI-specific fields.
- Support upload, delete, gallery browsing, and filename search.
- Derive captured date from EXIF when available; allow a fallback to upload time.
- Work as both a regular web app and a progressive web app (PWA).
- Continue using FastAPI + SQLite (SQLModel) with files stored on disk.

## 2. Non-Goals
- No AI-specific metadata (prompt, model, rating, references, tags, comments).
- No video ingestion for the base fork.
- No external auth, sharing, or cloud storage.

## 3. High-Level Architecture
- **FastAPI backend** serves JSON APIs and static files from a single service.
- **SQLite + SQLModel** persist minimal metadata.
- **Images directory** remains the source of truth for uploaded files.
- **Frontend** remains the current SPA (Vite bundle). Only prune fields and adjust labels.
- **PWA** uses a manifest + service worker for app shell caching.

## 4. Data & Storage Schema
SQLModel `Photo` model:
- `id` (UUID PK)
- `file_name` (string, required, unique)
- `captured_at` (datetime, nullable)
- `created_at` (datetime, default now)
- `updated_at` (datetime, default now)

Derived attributes (not stored unless already present):
- Width/height may be calculated at upload time if desired, but are optional.

## 5. API Surface (JSON unless noted)
- `GET /` – serves gallery HTML.
- `GET /images/{file_name}` – static image serving via `StaticFiles`.
- `GET /api/photos` – list with filters: `q` (filename search), pagination (`page`, `page_size`).
- `GET /api/photos/{id}` – detail view (file name, captured date, URLs).
- `POST /api/photos` (multipart) – accepts `photo_file` (required). Captured date parsed from EXIF when possible. Returns created record.
- `DELETE /api/photos/{id}` – removes DB record and file on disk.

## 6. Frontend Experience
- Retain the current layout, spacing, and typography.
- Search bar stays and filters by filename.
- Gallery cards show thumbnail, filename, captured date (if any).
- Detail modal shows larger image, filename, captured date, and delete action.
- Upload modal remains in the same place/style but only accepts a file (no AI fields).

## 7. PWA Requirements
- `manifest.json` with icons, name, short_name, start_url, display, and theme colors.
- Service worker caches the app shell (HTML/CSS/JS); images use a network-first strategy.
- Ensure the app is installable on desktop and mobile.

## 8. Cleanup & Migration
- Remove AI-specific columns and endpoints from the schema and APIs.
- Prune frontend UI for AI metadata while preserving layout.
- Update tests to match the simplified model and endpoints.

## 9. Risks & Follow-Ups
- EXIF parsing must tolerate missing or malformed metadata.
- Removing AI fields could leave unused frontend utilities; ensure they are fully pruned.
- PWA caching strategy must avoid unbounded image storage.
