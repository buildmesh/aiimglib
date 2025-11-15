FROM python:3.11-slim AS base

WORKDIR /app

RUN pip install --upgrade pip uv

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

COPY app app
RUN mkdir -p images

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
