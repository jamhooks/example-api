"""Run the example API: ``uv run python main.py`` (http://127.0.0.1:8000)."""

from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "example_api.app:app_from_env",
        factory=True,
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        # The access log would print account numbers (in the path) and callers' phone
        # numbers (in the query string). An API that serves a call flow shouldn't.
        access_log=False,
    )
