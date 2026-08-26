# syntax=docker/dockerfile:1
#
# Worker image, multi-stage build.
#
# Stage "builder" uses the official uv static binary image (ghcr.io/astral-sh/uv) copied onto a
# slim python base, rather than installing uv via pip, so the resulting layer is reproducible and
# doesn't depend on PyPI for the build tool itself. `uv sync --frozen --no-dev` installs runtime
# dependencies only (no pytest/ruff/playwright) straight from the committed `uv.lock`, keeping the
# runtime image lean.

FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY src/ src/

RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN useradd --create-home --uid 1000 sandbox
WORKDIR /app
COPY --from=builder --chown=sandbox:sandbox /app /app
USER sandbox

ENTRYPOINT ["python", "-m", "sandbox.worker"]
