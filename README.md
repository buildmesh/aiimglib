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
```bash
docker compose up --build
```

### Legacy metadata import
If you have an older JSON export (see `docs/reference/legacy-json-format.md`), import it after running migrations:
```bash
uv run python scripts/import_legacy_json.py path/to/legacy.json
```
Use `--dry-run` to validate the data without writing to SQLite.

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
