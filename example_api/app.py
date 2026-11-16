"""An example backend for the Jamhooks example flows.

Each endpoint answers one HTTP Request node in the app's examples, with the JSON shape
that node's Response Mapping reads:

- ``GET /accounts/{account_number}``: ``example/account_lookup`` maps ``status`` and
  ``team_number``. An unknown account is a 404, which the flow sees as ``{{http_error}}``.
- ``GET /customers?phone=...``: ``example/priority_routing`` (its ``CRM_URL`` env var)
  maps ``tier`` and ``balance_due``. An unknown caller is a 200 with both set to null, so
  the flow's "Not in the CRM" rule (``tier`` is empty) matches.
- ``/anything``: ``example/nodes/data_tools`` (its ``ECHO_URL`` env var) maps
  ``json.tier``, the request body echoed back the way httpbin's ``/anything`` does.

The data is a JSON file (``data.json`` next to this module, or ``DATA_FILE``). Set
``API_TOKEN`` to require ``Authorization: Bearer <token>`` on every endpoint except
``/health``, the way a real backend would; the HTTP Request node sends it as a header.
"""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request

DEFAULT_DATA_FILE = Path(__file__).with_name("data.json")


def load_data(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "accounts": dict(data.get("accounts", {})),
        # Keyed by digits only, so "+1 202-555-0131" and "12025550131" find the same entry.
        "customers": {_digits(k): v for k, v in data.get("customers", {}).items()},
    }


def _digits(phone: str) -> str:
    return "".join(ch for ch in phone if ch.isdigit())


def create_app(data_file: Path | None = None, token: str | None = None) -> FastAPI:
    data = load_data(data_file or DEFAULT_DATA_FILE)

    def require_token(authorization: str | None = Header(default=None)) -> None:
        if not token:
            return
        expected = f"Bearer {token}"
        if authorization is None or not secrets.compare_digest(
            authorization.encode(), expected.encode()
        ):
            raise HTTPException(
                status_code=401,
                detail="missing or wrong bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    app = FastAPI(
        title="Jamhooks example API",
        version="0.1.0",
        description="Answers the HTTP Request nodes in the Jamhooks example flows.",
    )
    api = APIRouter(dependencies=[Depends(require_token)])

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.get("/accounts/{account_number}")
    def get_account(account_number: str) -> dict[str, Any]:
        account = data["accounts"].get(account_number)
        if account is None:
            raise HTTPException(status_code=404, detail="account not found")
        return {"account_number": account_number, **account}

    @api.get("/customers")
    def get_customer(phone: str = "") -> dict[str, Any]:
        # A "+" sent unencoded in a query string arrives as a space; comparing digits
        # only makes "?phone=+12025550131" and "?phone=%2B12025550131" the same lookup.
        customer = data["customers"].get(_digits(phone))
        if customer is None:
            return {"phone": phone.strip(), "found": False, "tier": None, "balance_due": None}
        return {"phone": phone.strip(), "found": True, **customer}

    @api.api_route("/anything", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    @api.api_route("/anything/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def anything(request: Request) -> dict[str, Any]:
        body = await request.body()
        try:
            parsed = json.loads(body) if body else None
        except ValueError:
            parsed = None
        # Headers are left out on purpose: they can carry a token.
        return {
            "method": request.method,
            "path": request.url.path,
            "args": dict(request.query_params),
            "json": parsed,
        }

    app.include_router(api)
    return app


def app_from_env() -> FastAPI:
    """The app as configured by the environment (``DATA_FILE``, ``API_TOKEN``)."""
    data_file = os.environ.get("DATA_FILE")
    return create_app(
        data_file=Path(data_file) if data_file else None,
        token=os.environ.get("API_TOKEN") or None,
    )
