FROM ghcr.io/astral-sh/uv:0.13.0-python3.13-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install only the locked production dependencies before copying source files.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# src/data/registries is copied with the application and remains read-only at runtime.
COPY src ./src

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "--app-dir", "/app/src", "bead_pattern.main:app", "--host", "0.0.0.0", "--port", "8000"]
