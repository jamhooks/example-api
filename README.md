# Jamhooks example API

A small HTTP API that answers the **HTTP Request** nodes in the Jamhooks example flows,
so you can try them on a real call without a backend of your own. It is a Cloudflare
Worker serving sample data from a JSON file, and is not meant for production.

The example flows call the public instance at `https://example.jamhooks.com` out of the
box. Run or deploy your own copy to change the data, try `API_TOKEN`, or see how a
backend for Jamhooks is put together.

## Run it locally

```bash
npm ci
npm run dev        # http://localhost:8787, in the real Workers runtime
npm test           # node's built-in test runner
```

Optional setting: the secret `API_TOKEN` requires `Authorization: Bearer <token>` on
every endpoint except `/health`. Locally, copy `.dev.vars.example` to `.dev.vars` and
set it there; in Cloudflare, run `npx wrangler secret put API_TOKEN`.

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

Edit `src/data.json` to change them.

## Use your own copy with the example flows

The Jamhooks app makes these requests, not Jambonz, so the API only has to be reachable
from the app: `http://127.0.0.1:8787` for `npm run dev` on the same machine, or your own
deployment (change `routes` in `wrangler.jsonc` to your domain).

1. In the editor, **New Flow → Load Example** and pick the flow.
2. Point it at your copy instead of `https://example.jamhooks.com`:
   - `example/account_lookup`: the URL is written into the **Look up account** node.
     Change it to `<your-api>/accounts/{{digits}}`.
   - `example/priority_routing`: set the env var `CRM_URL` to `<your-api>/customers`.
   - `example/nodes/data_tools`: set the env var `ECHO_URL` to `<your-api>/anything`.

   An env var's value comes from the Jambonz application's env vars (set in the
   Jambonz portal); without one, the default declared in the flow is used.
3. **Deploy**, then call it, and follow the requests in the editor's **Debug** pane.
   **Simulate** does not send HTTP requests, so it never reaches this API.

The app setting `HTTP_REQUEST_ALLOW_PRIVATE` must stay `true` (the default) for the app
to reach a copy on a private or loopback address. With `API_TOKEN` set, add a header to
the HTTP Request node: `Authorization` → `Bearer {{env_vars.API_TOKEN}}`, with
`API_TOKEN` declared as an obscure env var.

The API logs no requests, and Workers Logs are off (`wrangler.jsonc`): request paths
carry account numbers and query strings callers' phone numbers. Keep it that way in
your own backend.

## Deployment

Every push to `master` deploys to `https://example.jamhooks.com`: the `deploy` job in
`.github/workflows/ci.yml` runs after the tests pass, then checks that the deployed API
answers. Pull requests and other branches only run the tests and bundle the Worker.

One-time setup:

1. `jamhooks.com` is a zone in the Cloudflare account. The first deploy creates the
   `example` DNS record and its certificate (`custom_domain` in `wrangler.jsonc`).
2. In Cloudflare, create an API token from the **Edit Cloudflare Workers** template,
   limited to that account and the `jamhooks.com` zone.
3. In this repository's **Settings → Environments**, create `production`, limit its
   deployment branches to `master`, and add two environment secrets:
   `CLOUDFLARE_API_TOKEN` (the token) and `CLOUDFLARE_ACCOUNT_ID` (on the account's
   **Workers & Pages** overview page).

## Licence

[MIT](LICENSE). Copy it, change it, build your own backend from it.
