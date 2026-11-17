import assert from 'node:assert/strict';
import { test } from 'node:test';

import worker from '../src/index.js';
import data from '../src/data.json' with { type: 'json' };

const BASE = 'https://example.jamhooks.com';

async function call(path, { method = 'GET', body, headers = {}, env = {} } = {}) {
  const init = { method, headers: { ...headers } };
  if (body !== undefined) {
    init.body = JSON.stringify(body);
    init.headers['Content-Type'] = 'application/json';
  }
  const response = await worker.fetch(new Request(BASE + path, init), env);
  return { status: response.status, body: await response.json(), response };
}

test('health', async () => {
  assert.deepEqual((await call('/health')).body, { status: 'ok' });
});

// --- example/account_lookup: maps `status` and `team_number` ---------------------------

test('an active account has a status and a team number', async () => {
  const { body } = await call('/accounts/100001');
  assert.equal(body.status, 'active');
  assert.equal(body.team_number, '+12025550121');
});

test('a closed account is found but not active', async () => {
  const { status, body } = await call('/accounts/300001');
  assert.equal(status, 200);
  assert.equal(body.status, 'closed');
});

test('an unknown account is a 404', async () => {
  // The flow sees this as {{http_error}} and takes its "not found" branch.
  assert.equal((await call('/accounts/999999')).status, 404);
});

test('a malformed escape in the account number is a 404, not a crash', async () => {
  assert.equal((await call('/accounts/%E0%A4%A')).status, 404);
});

// --- example/priority_routing: maps `tier` and `balance_due` ---------------------------

test('a known caller has a tier and a balance', async () => {
  // What the app sends: {{from}} percent-encoded in the query.
  const { body } = await call('/customers?phone=%2B12025550131');
  assert.equal(body.tier, 'platinum');
  assert.equal(body.balance_due, 0);
});

test('an unencoded plus finds the same caller', async () => {
  // A raw "+" in a query string decodes to a space.
  const { body } = await call('/customers?phone=+12025550133');
  assert.equal(body.tier, 'standard');
  assert.equal(body.balance_due, 42.5);
});

test('an unknown caller is a 200 with null fields', async () => {
  // Null, not a 404: the flow's "Not in the CRM" rule matches an empty tier, and a 404
  // would leave the tier its Start node set instead.
  const { status, body } = await call('/customers?phone=%2B12025550199');
  assert.equal(status, 200);
  assert.equal(body.tier, null);
  assert.equal(body.balance_due, null);
});

// --- example/nodes/data_tools: maps `json.tier` ----------------------------------------

test('anything echoes the JSON body', async () => {
  const { body } = await call('/anything', {
    method: 'POST',
    body: { customer: 'Example', tier: 'gold' },
  });
  assert.deepEqual(body.json, { customer: 'Example', tier: 'gold' });
  assert.equal(body.method, 'POST');
});

test('anything echoes query args and accepts a subpath', async () => {
  const { body } = await call('/anything/some/path?a=1');
  assert.deepEqual(body.args, { a: '1' });
  assert.equal(body.path, '/anything/some/path');
  assert.equal(body.json, null);
});

test('anything does not echo headers', async () => {
  const { body } = await call('/anything', {
    method: 'POST',
    body: {},
    headers: { Authorization: 'Bearer x' },
  });
  assert.equal('headers' in body, false);
});

test('an unknown path is a 404', async () => {
  assert.equal((await call('/nope')).status, 404);
});

// --- API_TOKEN ---------------------------------------------------------------------------

test('a token is required once set', async () => {
  const env = { API_TOKEN: 's3cret' };
  assert.equal((await call('/accounts/100001', { env })).status, 401);
  const wrong = { Authorization: 'Bearer nope' };
  assert.equal((await call('/accounts/100001', { env, headers: wrong })).status, 401);
  const right = { Authorization: 'Bearer s3cret' };
  assert.equal((await call('/accounts/100001', { env, headers: right })).status, 200);
});

test('health needs no token', async () => {
  assert.equal((await call('/health', { env: { API_TOKEN: 's3cret' } })).status, 200);
});

// --- data ----------------------------------------------------------------------------------

test('the sample data uses only fictional numbers', () => {
  // 555-0100 to 555-0199 is reserved for fiction in the North American plan.
  const numbers = [
    ...Object.keys(data.customers),
    ...Object.values(data.accounts).map((a) => a.team_number).filter(Boolean),
  ];
  assert.ok(numbers.length > 0);
  for (const number of numbers) assert.match(number, /^\+1\d{3}5550\d{3}$/);
  for (const number of numbers) assert.equal(number[9], '1', number);
});
