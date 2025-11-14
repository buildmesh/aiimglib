# AI Image Library

FastAPI backend powering a searchable gallery of AI-generated images.

## Requirements
- Python 3.11 (managed via [uv](https://docs.astral.sh/uv/))
- uv installed on your PATH

## Setup
```bash
uv sync
```

## Development Server
Run the API with auto-reload:
```bash
uv run uvicorn app.main:app --reload
```

## Tests
```bash
uv run pytest
```

## Docker
Build and run the service using Docker Compose:
```bash
docker compose up --build
```
