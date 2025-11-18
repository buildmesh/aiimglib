# AI Image Library

FastAPI backend powering a searchable gallery of AI-generated images.

## Requirements
- Python 3.11 (managed via [uv](https://docs.astral.sh/uv/))
- Node 20+ (for the frontend build pipeline)

## Setup
Install backend dependencies with uv:
```bash
uv sync
```

Install frontend dependencies and build the static bundle:
```bash
cd frontend
npm install
npm run build
```
> The Vite build writes to `app/static/`. Always edit sources in `frontend/` and rebuild rather than modifying files in `app/static/` directly.

## Running the Backend
### Local development (hot reload)
```bash
uv run uvicorn app.main:app --reload
```

### Docker Compose
Ensure the bind-mount directories exist on the host:
```bash
mkdir -p images data
```

Build and run:
```bash
docker compose up --build
```
The container stores uploads in `./images` and the SQLite database at `./data/app.db`.

### Legacy metadata import
If you have an older JSON export (see `docs/reference/legacy-json-format.md`), place the JSON file and its referenced images/thumbnails in the same directory, then run:
```bash
uv run python scripts/import_legacy_json.py path/to/legacy.json
```
Use `--dry-run` to validate paths without writing to SQLite. The importer copies each referenced image into `images/` and creates matching database rows—no manual file copying required.

Importer behavior highlights:
- Video files are detected by extension (`.mp4`, `.webm`, `.mov`, `.mkv`) and **must** provide a `thumbnail_file` entry so the gallery has a still frame to render.
- Prompt reference chains are preserved: legacy IDs are remapped to the new UUIDs so the frontend can resolve source links, and derived entries without an explicit thumbnail inherit the first referenced asset's thumbnail/file automatically.
- When a legacy entry supplies a dedicated thumbnail image, place that file next to the JSON export so the importer can copy it alongside the main media.

## Using the App
- Visit `http://localhost:8000/` to open the gallery UI.
- Click **Add Image** to upload a new file with prompt metadata.
- Use the inline edit buttons on each card to update prompts, tags, notes, or ratings.
- Filters (search, tags, ratings, date range) issue requests against `/api/images`.

## Tests
Run the full suite (backend + API + frontend smoke tests):
```bash
uv run pytest -v
```
