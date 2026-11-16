from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from example_api.app import DEFAULT_DATA_FILE, create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


# --- example/account_lookup: maps `status` and `team_number` ----------------------


def test_an_active_account_has_a_status_and_a_team_number(client: TestClient) -> None:
    body = client.get("/accounts/100001").json()
    assert body["status"] == "active"
    assert body["team_number"] == "+12025550121"


def test_a_closed_account_is_found_but_not_active(client: TestClient) -> None:
    resp = client.get("/accounts/300001")
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"


def test_an_unknown_account_is_a_404(client: TestClient) -> None:
    # The flow sees this as {{http_error}} and takes its "not found" branch.
    assert client.get("/accounts/999999").status_code == 404


# --- example/priority_routing: maps `tier` and `balance_due` ----------------------


def test_a_known_caller_has_a_tier_and_a_balance(client: TestClient) -> None:
    # What the app sends: {{from}} percent-encoded in the query.
    body = client.get("/customers?phone=%2B12025550131").json()
    assert body["tier"] == "platinum"
    assert body["balance_due"] == 0


def test_an_unencoded_plus_finds_the_same_caller(client: TestClient) -> None:
    # A raw "+" in a query string decodes to a space.
    body = client.get("/customers?phone=+12025550133").json()
    assert body["tier"] == "standard"
    assert body["balance_due"] == 42.5


def test_an_unknown_caller_is_a_200_with_null_fields(client: TestClient) -> None:
    # Null, not a 404: the flow's "Not in the CRM" rule matches an empty tier, and a
    # 404 would leave the tier its Start node set instead.
    resp = client.get("/customers?phone=%2B12025550199")
    assert resp.status_code == 200
    assert resp.json()["tier"] is None
    assert resp.json()["balance_due"] is None


# --- example/nodes/data_tools: maps `json.tier` -----------------------------------


def test_anything_echoes_the_json_body(client: TestClient) -> None:
    resp = client.post("/anything", json={"customer": "Example", "tier": "gold"})
    assert resp.json()["json"] == {"customer": "Example", "tier": "gold"}
    assert resp.json()["method"] == "POST"


def test_anything_echoes_query_args_and_accepts_a_subpath(client: TestClient) -> None:
    body = client.get("/anything/some/path?a=1").json()
    assert body["args"] == {"a": "1"}
    assert body["path"] == "/anything/some/path"
    assert body["json"] is None


def test_anything_does_not_echo_headers(client: TestClient) -> None:
    body = client.post("/anything", json={}, headers={"Authorization": "Bearer x"}).json()
    assert "headers" not in body


# --- API_TOKEN ---------------------------------------------------------------------


@pytest.fixture
def guarded() -> TestClient:
    return TestClient(create_app(token="s3cret"))


def test_a_token_is_required_once_set(guarded: TestClient) -> None:
    assert guarded.get("/accounts/100001").status_code == 401
    wrong = {"Authorization": "Bearer nope"}
    assert guarded.get("/accounts/100001", headers=wrong).status_code == 401
    right = {"Authorization": "Bearer s3cret"}
    assert guarded.get("/accounts/100001", headers=right).status_code == 200


def test_health_needs_no_token(guarded: TestClient) -> None:
    assert guarded.get("/health").status_code == 200


# --- data --------------------------------------------------------------------------


def test_another_data_file_can_be_used(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    path.write_text(json.dumps({"accounts": {"1": {"status": "active"}}}))
    client = TestClient(create_app(data_file=path))
    assert client.get("/accounts/1").json()["status"] == "active"
    assert client.get("/accounts/100001").status_code == 404


def test_the_sample_data_uses_only_fictional_numbers() -> None:
    # 555-0100 to 555-0199 is reserved for fiction in the North American plan.
    data = json.loads(DEFAULT_DATA_FILE.read_text())
    numbers = list(data["customers"]) + [
        a["team_number"] for a in data["accounts"].values() if a["team_number"]
    ]
    assert numbers
    for number in numbers:
        assert number.startswith("+1") and number[5:9] == "5550" and number[9] == "1", number
