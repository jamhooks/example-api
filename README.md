# Jamhooks example API

A small HTTP API that answers the **HTTP Request** nodes in the Jamhooks example flows,
so you can try them on a real call without a backend of your own. It serves sample data
from a JSON file and is not meant for production.

The example flows call the public instance at `https://example.jamhooks.com` out of the
box. Run your own copy to change the data, try `API_TOKEN`, or see how a backend for
Jamhooks is put together.

## Run it

```bash
uv sync
uv run python main.py          # http://127.0.0.1:8000, interactive docs at /docs
```

Or with Docker:

```bash
docker build -t jamhooks-example-api .
docker run --rm -p 8000:8000 jamhooks-example-api
```

Settings (all optional, see `.env.example`): `API_TOKEN` requires
`Authorization: Bearer <token>` on every endpoint except `/health`; `DATA_FILE` reads
another data file instead of `example_api/data.json`; `HOST` and `PORT` set where
`main.py` listens.

## Endpoints

| Endpoint | Used by (Load Example) | Returns |
|---|---|---|
| `GET /accounts/{account_number}` | `example/account_lookup` | `status`, `team_number`; an unknown account is a **404** |
| `GET /customers?phone=...` | `example/priority_routing` | `tier`, `balance_due`; an unknown caller is a **200 with both `null`** |
| `GET\|POST\|PUT\|PATCH\|DELETE /anything` | `example/nodes/data_tools` | the request echoed back: `method`, `path`, `args`, and the JSON body under `json` (like httpbin's `/anything`) |
| `GET /health` | | `{"status": "ok"}` |

The two "not found" answers differ on purpose, because each flow reads them differently.
`account_lookup` treats a failed request (`{{http_error}}`) as "no active account", so a
404 is right there. `priority_routing` has a "Not in the CRM" rule that matches an
**empty** `tier`; a 404 would leave `tier` at the value its Start node set, so an unknown
caller gets a 200 with `tier: null` instead.

## Sample data

All phone numbers are in the 555-0100 to 555-0199 range, which is reserved for fiction.

| Account | `status` | `team_number` | `account_lookup` takes |
|---|---|---|---|
| `100001` | active | +12025550121 | transfer to the account team |
| `100002` | active | +12025550122 | transfer to the account team |
| `200001` | suspended | +12025550123 | not found message |
| `300001` | closed | `null` | not found message |
| anything else | (404) | | not found message |

| Caller (`from`) | `tier` | `balance_due` | `priority_routing` takes |
|---|---|---|---|
| +12025550131 | platinum | 0 | Platinum (VIP line), when `VIP_LINE_OPEN` is true |
| +12025550132 | gold | 0 | Gold |
| +12025550133 | standard | 42.5 | Payment overdue |
| +12025550134 | standard | 0 | the fallback |
| anything else | `null` | `null` | Not in the CRM |

Edit `example_api/data.json` (or point `DATA_FILE` at your own copy) to change them.

## Use your own copy with the example flows

The Jamhooks app makes these requests, not Jambonz, so the API only has to be reachable
from the app. Use an address the app can resolve: `http://127.0.0.1:8000` when both run on
your machine without Docker; from the app's container, the host's address or a shared
Docker network (`localhost` inside a container is the container itself).

1. In the editor, **New Flow → Load Example** and pick the flow.
2. Point it at your copy instead of `https://example.jamhooks.com`:
   - `example/account_lookup`: the URL is written into the **Look up account** node.
     Change it to `http://<api-host>:8000/accounts/{{digits}}`.
   - `example/priority_routing`: set the env var `CRM_URL` to
     `http://<api-host>:8000/customers`.
   - `example/nodes/data_tools`: set the env var `ECHO_URL` to
     `http://<api-host>:8000/anything`.

   An env var's value comes from the Jambonz application's env vars (set in the
   Jambonz portal); without one, the default declared in the flow is used.
3. **Deploy**, then call it, and follow the requests in the editor's **Debug** pane.
   **Simulate** does not send HTTP requests, so it never reaches this API.

Two app settings matter. `HTTP_REQUEST_ALLOW_PRIVATE` must stay `true` (the default)
for the app to reach this API on a private or loopback address. With `API_TOKEN` set,
add a header to the HTTP Request node: `Authorization` → `Bearer {{env_vars.API_TOKEN}}`,
with `API_TOKEN` declared as an obscure env var.

The API logs no requests: the access log would print account numbers (in the path) and
callers' phone numbers (in the query string). Keep it that way in your own backend.

## Development

```bash
uv run pytest
uv run ruff check .
```

CI (`.github/workflows/ci.yml`) runs both and builds and smoke-tests the image.

## Licence

[MIT](LICENSE). Copy it, change it, build your own backend from it.
