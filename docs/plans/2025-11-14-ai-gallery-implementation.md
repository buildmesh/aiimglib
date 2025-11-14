# AI Gallery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a FastAPI + SQLModel web app that serves a searchable gallery of AI-generated images, supports uploads, and persists metadata in SQLite.

**Architecture:** Single FastAPI service exposes REST APIs, serves static frontend assets, and manages SQLite persistence via SQLModel. Images live on disk under `images/`, metadata lives in `app.db`, and the frontend is a lightweight SPA hitting `/api/*` endpoints.

**Tech Stack:** Python 3.11, FastAPI, SQLModel/SQLAlchemy, Uvicorn, Pydantic, HTMX/Alpine.js, Vite (optional) or vanilla JS, pytest + httpx for tests.

### Task 1: Project Scaffolding & Dependencies

**Files:**
- Create: `pyproject.toml`, `app/__init__.py`, `app/config.py`, `app/main.py`, `images/.gitkeep`
- Modify: `README.md`
- Test: `tests/test_health.py`

**Step 1: Initialize project metadata**

Create `pyproject.toml` with FastAPI, SQLModel, uvicorn, python-multipart, aiofiles, pytest, httpx, and any frontend build deps (if bundling). Configure `[tool.pytest.ini_options]` to set `testpaths = ["tests"]`.

**Step 2: Scaffold FastAPI entrypoint**

Create `app/main.py` with minimal app exposing `GET /healthz` returning `{ "status": "ok" }`. Add `app/config.py` for settings (DB path, image dir) using Pydantic `BaseSettings`.

```python
# app/main.py
from fastapi import FastAPI
from .config import settings

app = FastAPI(title="AI Image Library")

@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

**Step 3: Write failing health test**

Create `tests/test_health.py` verifying `/healthz` returns 200 + body.

```python
from fastapi.testclient import TestClient
from app.main import app

def test_health_endpoint():
    client = TestClient(app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

**Step 4: Run pytest to ensure health test passes**

Run: `pytest tests/test_health.py -v`
Expected: PASS.

**Step 5: Document setup instructions**

Add to `README.md`: Python version, how to install deps (`pip install -e .[dev]` or `poetry install`), run server (`uvicorn app.main:app --reload`), run tests.

**Step 6: Commit scaffolding**

```bash
git add pyproject.toml app/main.py app/config.py README.md tests/test_health.py images/.gitkeep
git commit -m "chore: scaffold FastAPI project"
```

### Task 2: Database Layer & Models

**Files:**
- Create: `app/database.py`, `app/models.py`, `app/schemas.py`, `scripts/import_legacy_json.py`
- Test: `tests/test_models.py`

**Step 1: Implement database helper**

`app/database.py` should expose `engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})` and `SessionLocal = sessionmaker(...)`. Provide dependency `get_session()` yielding `Session`.

**Step 2: Define SQLModel models**

In `app/models.py`, define:

```python
class Image(SQLModel, table=True):
    id: str = Field(primary_key=True, default_factory=lambda: str(uuid4()))
    file_name: str
    prompt_text: str
    prompt_meta: dict | None = Field(default=None, sa_column=Column(JSON))
    ai_model: str | None
    notes: str | None
    rating: int | None = Field(default=None, ge=0, le=5)
    captured_at: datetime | None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Tag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)

class ImageTagLink(SQLModel, table=True):
    image_id: str = Field(foreign_key="image.id", primary_key=True)
    tag_id: int = Field(foreign_key="tag.id", primary_key=True)
```

Expose relationship fields for tags.

**Step 3: Create Pydantic schemas**

`app/schemas.py` will define request/response models (e.g., `ImageCreate`, `ImageUpdate`, `ImageRead`, `TagRead`). Include list-of-tags fields and prompt metadata union type (string | list).

**Step 4: Auto-create tables on startup**

Modify `app/main.py` to import `app.models` and call `SQLModel.metadata.create_all(engine)` inside a startup event.

**Step 5: Write model tests**

`tests/test_models.py` uses an in-memory SQLite engine to create tables, insert `Image` + tags, and verify relationship behavior.

```python
from sqlmodel import Session, SQLModel, create_engine
from app import models

engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)
with Session(engine) as session:
    img = models.Image(file_name="foo.png", prompt_text="test")
    session.add(img)
    session.commit()
    assert session.get(models.Image, img.id)
```

**Step 6: Legacy import script**

`scripts/import_legacy_json.py` reads existing JSON file, iterates entries, saves image rows + tags (creating if missing). Provide CLI usage instructions and dry-run option.

**Step 7: Run tests**

`pytest tests/test_models.py -v`

**Step 8: Commit database layer**

```bash
git add app/database.py app/models.py app/schemas.py scripts/import_legacy_json.py tests/test_models.py app/main.py
git commit -m "feat: add SQLModel schema and legacy importer"
```

### Task 3: CRUD Services & Tag Utilities

**Files:**
- Create: `app/crud.py`, `app/services/tags.py`
- Modify: `app/models.py` (relationships), `app/schemas.py`
- Test: `tests/test_crud.py`

**Step 1: Implement tag utilities**

`app/services/tags.py` exposes `ensure_tags(session, names: list[str]) -> list[Tag]` that lowercases/dedupes names, creates missing rows, returns Tag objects.

**Step 2: Build CRUD functions**

`app/crud.py` functions:
- `list_images(session, filters)` returning `(items, total)`
- `get_image(session, image_id)` raising `HTTPException` 404
- `create_image(session, data)` linking tags
- `update_image(session, image_id, data)`
- `delete_image(session, image_id)` cleaning tag links
Each should manage associations via helper and update timestamps.

**Step 3: Tests for CRUD**

`tests/test_crud.py` uses temp SQLite DB + tmpdir for files. Validate create/list/update/delete flows and tag reuse.

```python
def test_create_image_saves_tags(tmp_path):
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        payload = ImageCreate(...)
        created = create_image(session, payload, image_path="foo.png")
        assert created.tags == ["foo"]
```

**Step 4: Run pytest**

`pytest tests/test_crud.py -v`

**Step 5: Commit**

```bash
git add app/crud.py app/services/tags.py tests/test_crud.py app/models.py app/schemas.py
git commit -m "feat: add CRUD layer with tag helpers"
```

### Task 4: API Routers & Upload Handling

**Files:**
- Create: `app/api/__init__.py`, `app/api/images.py`, `app/api/tags.py`, `app/dependencies.py`, `app/services/files.py`
- Modify: `app/main.py`
- Test: `tests/test_images_api.py`, `tests/test_tags_api.py`

**Step 1: File service**

`app/services/files.py` handles saving uploads securely: `save_upload(upload: UploadFile) -> str` storing to `settings.images_dir` with UUID filenames, returning relative path. Provide helper to delete files.

**Step 2: Dependencies**

`app/dependencies.py` adds `Session` dependency and `PaginationParams` Pydantic model to parse query args.

**Step 3: Images router**

`app/api/images.py` defines router with endpoints from design (`GET /api/images`, `GET /api/images/{id}`, `POST`, `PUT`, `POST /{id}/file`, `DELETE`). Use CRUD functions + file service. Validate prompt format (string or list) before persisting.

**Step 4: Tags router**

`app/api/tags.py` exposes `GET /api/tags` returning tag list + usage counts via `select(Tag, func.count(...))`.

**Step 5: Mount routers and static files**

In `app/main.py`, include routers (`app.include_router(image_router, prefix="/api")`, etc.) and mount `StaticFiles(directory=settings.images_dir)` at `/images`. Serve `/` later via frontend build.

**Step 6: API tests**

`tests/test_images_api.py` uses `TestClient`, temp DB, and monkeypatched settings to temp directories. Cover:
- List filters (text, rating, tags)
- Upload (multipart) storing file + metadata, verifying DB + file
- Update metadata reflects in response
- Delete removes file
`tests/test_tags_api.py` asserts `/api/tags` returns names + counts.

**Step 7: Run pytest suite**

`pytest tests/test_images_api.py tests/test_tags_api.py -v`

**Step 8: Commit API layer**

```bash
git add app/api app/dependencies.py app/services/files.py app/main.py tests/test_images_api.py tests/test_tags_api.py
git commit -m "feat: add REST API and upload handling"
```

### Task 5: Frontend Gallery & Build Pipeline

**Files:**
- Create: `frontend/index.html`, `frontend/main.js`, `frontend/styles.css`, `frontend/package.json`, `frontend/vite.config.js`
- Create build output dir: `app/static/` (generated by `npm run build`)
- Modify: `app/main.py` to serve static bundle at `/`
- Test: `tests/test_frontend_smoke.py` (optional HTTP GET check)

**Step 1: Initialize frontend**

Use Vite (vanilla) in `frontend/`. `package.json` scripts: `dev`, `build`, `preview`. Install HTMX/Alpine as dependencies. Configure `vite.config.js` to output to `../app/static`.

**Step 2: Implement gallery markup**

`frontend/index.html` contains root divs, search form, modals for add/edit. `main.js` fetches `/api/images`, renders grid, wires filters, handles add/edit modals with fetch calls. `styles.css` for responsive layout.

**Step 3: Build pipeline integration**

Add `npm run build` step to generate `app/static/`. Update `app/main.py` to serve `StaticFiles(directory="app/static", html=True)` mounted at `/`, with fallback to `index.html`.

**Step 4: Frontend smoke test**

`tests/test_frontend_smoke.py` uses `TestClient` to GET `/` ensuring HTML loads and references `/api/images` endpoints.

```python
def test_homepage_served(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "ai gallery" in resp.text.lower()
```

**Step 5: Manual verification**

1. Run backend: `uvicorn app.main:app --reload`
2. In another terminal: `cd frontend && npm install && npm run build`
3. Visit `http://localhost:8000/`, upload sample image, edit metadata, search by tag.

**Step 6: Commit frontend**

```bash
git add frontend package-lock.json app/static app/main.py tests/test_frontend_smoke.py
git commit -m "feat: add frontend gallery and bundle"
```

### Task 6: Documentation & Final Verification

**Files:**
- Modify: `README.md`, `docs/plans/2025-11-14-ai-gallery-design.md` (update status), `docs/plans/2025-11-14-ai-gallery-implementation.md` (add execution notes if needed)
- Test: `pytest -v`

**Step 1: Document workflows**

Update README with sections for "Running Backend", "Building Frontend", "Uploading Images", "Legacy Import". Include command snippets.

**Step 2: Full test run**

`pytest -v` ensuring entire suite passes.

**Step 3: Optional linting**

`ruff check app tests` if linting configured.

**Step 4: Commit docs + final fixes**

```bash
git add README.md docs/plans/*.md
git commit -m "docs: add usage instructions"
```

**Step 5: Tag ready state**

Run `uvicorn app.main:app --reload`, manual walkthrough confirming upload/search/edit flows. Capture screenshots for future reference.

---

Plan complete and saved to `docs/plans/2025-11-14-ai-gallery-implementation.md`. Two execution options:
1. **Subagent-Driven (this session)** – I’ll dispatch fresh subagents per task with reviews between tasks for tight feedback loops.
2. **Parallel Session (separate)** – Open a new session/worktree that uses `superpowers:executing-plans` to implement tasks in batches with checkpoints.

Which approach would you like to use?
