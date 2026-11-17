# AGENTS.md

Working guide for AI coding agents (and humans) in the Jamhooks example API.

## What this is

A Cloudflare Worker that answers the HTTP Request nodes in the Jamhooks example flows
(`examples/*.json` in the app repo, `jamhooks/jamhooks`) with sample data, so the flows
can be tried on a real call. It is a teaching example, not a product: plain JavaScript,
no framework, no runtime dependencies, one JSON data file. This repository is public.

The app's example flows call the public instance at `https://example.jamhooks.com`, and
every push to `master` deploys there. A change to a response shape reaches every user of
those flows as soon as it is merged.

## Commands

```bash
npm ci                 # install wrangler from package-lock.json
npm run dev            # http://localhost:8787 (workerd, the real Workers runtime)
npm test               # node --test over test/*.test.js
npm run check          # bundle the Worker as a deploy would, without uploading
```

Node's version is in `.node-version`. When starting the dev server from an agent, run it
in the background and stop it when done.

## Where things live

| Path | What |
|---|---|
| `src/index.js` | The whole API: one `fetch` handler, the routes, the optional token check |
| `src/data.json` | The sample accounts and customers |
| `test/index.test.js` | One test per behaviour a flow relies on |
| `wrangler.jsonc` | Worker name, compatibility date, the `example.jamhooks.com` route, logs off |
| `.github/workflows/ci.yml` | Tests and bundle on pull requests and `master` (no deploy) |

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

## Deployment

Cloudflare Workers Builds deploys `master` (README, "Deployment"): it runs
`npm ci && npm test` and then `npx wrangler deploy`, so a failing test stops the deploy.
No Cloudflare credentials live in GitHub, and GitHub Actions never deploys. Wrangler is
pinned to an exact version in `package.json` and installed from `package-lock.json`.
Never deploy by hand from a branch.

## Rules

- Never write the em-dash character (U+2014); rewrite the sentence instead.
- Sample data is fictional: phone numbers only in the 555-0100 to 555-0199 range
  (`+1202555 01xx`, a test holds it), no real names, `example.com` for domains.
- Never log a caller's number, digits or a URL's query string: no `console.log` of a
  request, and Workers Logs stay off.
- Never commit secrets. `API_TOKEN` is a Worker secret (`wrangler secret put`); local
  values go in `.dev.vars` (untracked, see `.dev.vars.example`). Never read or print
  `.dev.vars` or a `.env` file.
- Every GitHub Action is pinned to a full commit SHA with the release in a comment, and
  the runner is pinned (`ubuntu-24.04`). Never replace a pin with a tag; Dependabot
  proposes the bumps.
- Default branch is `master`. Commit only when asked; ask before pushing, tagging or
  releasing.
