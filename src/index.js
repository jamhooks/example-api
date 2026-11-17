// An example backend for the JamHooks example flows, as a Cloudflare Worker.
//
// Each endpoint answers one HTTP Request node in the app's examples, with the JSON shape
// that node's Response Mapping reads:
//
// - GET /accounts/{account_number}: example/account_lookup maps `status` and
//   `team_number`. An unknown account is a 404, which the flow sees as {{http_error}}.
// - GET /customers?phone=...: example/priority_routing (its CRM_URL env var) maps `tier`
//   and `balance_due`. An unknown caller is a 200 with both set to null, so the flow's
//   "Not in the CRM" rule (`tier` is empty) matches.
// - /anything: example/nodes/data_tools (its ECHO_URL env var) maps `json.tier`, the
//   request body echoed back the way httpbin's /anything does.
//
// Set the API_TOKEN secret to require `Authorization: Bearer <token>` on every endpoint
// except /health, the way a real backend would; the HTTP Request node sends it as a
// header.
//
// Nothing here logs a request: the path carries account numbers and the query string
// callers' phone numbers.

import data from './data.json' with { type: 'json' };

const ECHO_METHODS = new Set(['GET', 'POST', 'PUT', 'PATCH', 'DELETE']);

// Keyed by digits only, so "+1 202-555-0131" and "12025550131" find the same entry.
const digits = (phone) => phone.replace(/\D/g, '');
const customers = new Map(
  Object.entries(data.customers ?? {}).map(([phone, record]) => [digits(phone), record]),
);
const accounts = new Map(Object.entries(data.accounts ?? {}));

function json(body, status = 200, headers = {}) {
  return Response.json(body, { status, headers });
}

const encoder = new TextEncoder();

// Compares in time that depends only on the length, so the token can't be guessed a
// character at a time from response times.
function sameText(a, b) {
  const x = encoder.encode(a);
  const y = encoder.encode(b);
  if (x.length !== y.length) return false;
  let diff = 0;
  for (let i = 0; i < x.length; i++) diff |= x[i] ^ y[i];
  return diff === 0;
}

function isAuthorized(request, token) {
  if (!token) return true;
  return sameText(request.headers.get('Authorization') ?? '', `Bearer ${token}`);
}

function decodeSegment(segment) {
  try {
    return decodeURIComponent(segment);
  } catch {
    return null; // a malformed %-escape names no account
  }
}

async function echo(request, url) {
  const text = await request.text();
  let parsed = null;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = null;
    }
  }
  // Headers are left out on purpose: they can carry a token.
  return json({
    method: request.method,
    path: url.pathname,
    args: Object.fromEntries(url.searchParams),
    json: parsed,
  });
}

export default {
  async fetch(request, env = {}) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (path === '/health' && request.method === 'GET') return json({ status: 'ok' });

    if (!isAuthorized(request, env.API_TOKEN)) {
      return json({ detail: 'missing or wrong bearer token' }, 401, {
        'WWW-Authenticate': 'Bearer',
      });
    }

    const account = path.match(/^\/accounts\/([^/]+)$/);
    if (account && request.method === 'GET') {
      const number = decodeSegment(account[1]);
      const record = number === null ? undefined : accounts.get(number);
      if (!record) return json({ detail: 'account not found' }, 404);
      return json({ account_number: number, ...record });
    }

    if (path === '/customers' && request.method === 'GET') {
      // A "+" sent unencoded in a query string arrives as a space; comparing digits only
      // makes "?phone=+12025550131" and "?phone=%2B12025550131" the same lookup.
      const phone = (url.searchParams.get('phone') ?? '').trim();
      const record = customers.get(digits(phone));
      if (!record) return json({ phone, found: false, tier: null, balance_due: null });
      return json({ phone, found: true, ...record });
    }

    if ((path === '/anything' || path.startsWith('/anything/')) && ECHO_METHODS.has(request.method)) {
      return echo(request, url);
    }

    return json({ detail: 'not found' }, 404);
  },
};
