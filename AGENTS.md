# AGENTS.md

Working guide for AI coding agents (and humans) in the Jamhooks example API.

## What this is

A small FastAPI app that answers the HTTP Request nodes in the Jamhooks example flows
(`examples/*.json` in the app repo, `jamhooks/jamhooks`) with sample data, so the flows
can be tried on a real call. It is a teaching example, not a product: no database, no
persistence, one JSON data file. This repository is public.

The app's example flows call the public instance at `https://example.jamhooks.com`, so
a change to a response shape here reaches every user of those flows once it is deployed
there.

## Commands

```bash
uv sync                       # install from uv.lock
uv run python main.py         # http://127.0.0.1:8000 (docs at /docs)
uv run pytest                 # tests (warnings are errors)
uv run ruff check .
docker build -t jamhooks-example-api .
```

Always run Python through `uv run`. This is a non-package app (`[tool.uv] package =
false`).

## Where things live

| Path | What |
|---|---|
| `example_api/app.py` | The whole API: `create_app(data_file, token)` and `app_from_env()` |
| `example_api/data.json` | The sample accounts and customers |
| `main.py` | Local entry point (uvicorn, access log off) |
| `tests/test_api.py` | One test per behaviour a flow relies on |
| `Dockerfile` | Two-stage uv build, the same pinned base images as the app |

## The contract with the app's example flows

Every response shape here is read by a flow's Response Mapping in the app repo
(`../jamhooks/examples/` in the workspace). When you change a field name, a status code
or what "not found" returns, check the flow that reads it:

- `account_lookup` maps `status` and `team_number`, and treats `{{http_error}}` (any
  non-2xx) as "no active account".
- `priority_routing` maps `tier` and `balance_due`; its "Not in the CRM" rule needs an
  unknown caller to come back as a 200 with `tier: null`.
- `nodes_data_tools` maps `json.tier` from the echoed body.

The README's sample-data tables say which branch each sample record takes; keep them in
step with `data.json`. If an example flow in the app changes shape, this API follows.

## Rules

- Never write the em-dash character (U+2014); rewrite the sentence instead.
- Sample data is fictional: phone numbers only in the 555-0100 to 555-0199 range
  (`+1202555 01xx`, a test holds it), no real names, `example.com` for domains.
- Never log a caller's number, digits or a URL's query string: the access log stays off.
- Never commit secrets; settings are documented in `.env.example`. Never read or print
  a `.env` file.
- Every GitHub Action is pinned to a full commit SHA with the release in a comment, and
  the runner is pinned (`ubuntu-24.04`); base images are pinned by digest. Never replace
  a pin with a tag; Dependabot proposes the bumps.
- Default branch is `master`. Commit only when asked; ask before pushing, tagging or
  releasing.
