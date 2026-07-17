"""API tests for the expense routes, DynamoDB mocked with moto."""

from fastapi.testclient import TestClient

from conftest import WithGatewayClaims


def test_expenses_require_authentication():
    """Without forwarded JWT claims every expense route is 401."""
    from src.main import app

    unauthenticated = TestClient(app)
    assert unauthenticated.get("/expenses").status_code == 401
    assert unauthenticated.post("/expenses", json={}).status_code == 401
    assert unauthenticated.put("/expenses/x", json={}).status_code == 401
    assert unauthenticated.delete("/expenses/x").status_code == 401


def test_expenses_require_admin_group():
    """A valid token without the admin group is 403."""
    from src.main import app

    viewer = TestClient(
        WithGatewayClaims(app, {"email": "v@x.y", "cognito:groups": "[viewer]"})
    )
    assert viewer.get("/expenses").status_code == 403


def test_list_empty(client):
    res = client.get("/expenses")
    assert res.status_code == 200
    assert res.json() == []


def test_list_populated(client, sample_expense):
    client.post("/expenses", json=sample_expense)
    res = client.get("/expenses")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["description"] == sample_expense["description"]
    assert "id" in body[0]
    assert "_id" not in body[0]


def test_create_success(client, sample_expense):
    res = client.post("/expenses", json=sample_expense)
    assert res.status_code == 201
    body = res.json()
    assert body["description"] == sample_expense["description"]
    assert body["value"] == sample_expense["value"]
    assert body["recurrent"] is True
    assert isinstance(body["id"], str) and body["id"]


def test_create_roundtrips_through_dynamodb(client, sample_expense):
    created = client.post("/expenses", json=sample_expense).json()
    fetched = client.get("/expenses").json()[0]
    assert fetched == created


def test_create_generates_unique_ids(client, sample_expense):
    first = client.post("/expenses", json=sample_expense).json()
    second = client.post("/expenses", json=sample_expense).json()
    assert first["id"] != second["id"]


def test_create_validation_error(client):
    res = client.post("/expenses", json={"description": "missing fields"})
    assert res.status_code == 422


def test_create_value_not_a_number(client, sample_expense):
    bad = {**sample_expense, "value": "not-a-number"}
    res = client.post("/expenses", json=bad)
    assert res.status_code == 422


def test_update_success(client, sample_expense):
    created = client.post("/expenses", json=sample_expense).json()
    updated = {**sample_expense, "description": "Updated", "value": 99.0}
    res = client.put(f"/expenses/{created['id']}", json=updated)
    assert res.status_code == 200
    body = res.json()
    assert body["description"] == "Updated"
    assert body["value"] == 99.0
    assert body["id"] == created["id"]


def test_update_not_found(client, sample_expense):
    res = client.put("/expenses/does-not-exist", json=sample_expense)
    assert res.status_code == 404


def test_create_defaults_paid_to_false(client, sample_expense):
    res = client.post("/expenses", json=sample_expense)
    assert res.status_code == 201
    assert res.json()["paid"] is False


def test_update_marks_paid_and_persists(client, sample_expense):
    created = client.post("/expenses", json=sample_expense).json()
    res = client.put(f"/expenses/{created['id']}", json={**sample_expense, "paid": True})
    assert res.status_code == 200
    assert res.json()["paid"] is True
    # The paid flag survives a round-trip through DynamoDB.
    assert client.get("/expenses").json()[0]["paid"] is True


def test_update_toggles_paid_back_to_false(client, sample_expense):
    created = client.post("/expenses", json={**sample_expense, "paid": True}).json()
    res = client.put(
        f"/expenses/{created['id']}", json={**sample_expense, "paid": False}
    )
    assert res.status_code == 200
    assert res.json()["paid"] is False


def test_delete_success(client, sample_expense):
    created = client.post("/expenses", json=sample_expense).json()
    res = client.delete(f"/expenses/{created['id']}")
    assert res.status_code == 204
    assert client.get("/expenses").json() == []


def test_delete_not_found(client):
    res = client.delete("/expenses/does-not-exist")
    assert res.status_code == 404
