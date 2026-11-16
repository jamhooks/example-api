# Both base images are pinned by digest (the multi-arch index), keeping the tag for
# readability: a tag moves, a digest doesn't. Dependabot proposes the digest bumps.
# They are the same images the Jamhooks app builds on.

# --- Build stage: install the locked dependencies into a venv ------------------
FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim@sha256:81a1340fea1e72ad4a8e9a016128b0c61041cf182ea49fd788023e52842bc147 AS build

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=3.14

WORKDIR /app

# --locked, not --frozen: --frozen installs whatever uv.lock says even when
# pyproject.toml has moved on without it; --locked refuses that drift.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev && rm -f .venv/.lock

COPY example_api ./example_api

# --- Runtime stage --------------------------------------------------------------
FROM python:3.14-slim-trixie@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app
COPY --from=build /app /app

# Runs as nobody: the API reads its data file and writes nothing.
USER 65534:65534

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import os,sys,urllib.request; \
sys.exit(0 if urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('PORT','8000')}/health\", timeout=4).status==200 else 1)"

# --no-access-log: the access log would print account numbers (in the path) and
# callers' phone numbers (in the query string).
ENTRYPOINT ["sh", "-c", "exec uvicorn --factory example_api.app:app_from_env --host 0.0.0.0 --port ${PORT:-8000} --no-access-log"]
