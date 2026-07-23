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


# --- Month-scoped listing -------------------------------------------------


def test_list_with_month_includes_non_recurring_in_its_own_month(client):
    expense = {
        "description": "Gym",
        "deadline": "2026-07-15",
        "value": 45.0,
        "recurrent": False,
    }
    client.post("/expenses", json=expense)

    res = client.get("/expenses", params={"month": "2026-07"})
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_list_with_month_excludes_non_recurring_in_other_months(client):
    expense = {
        "description": "Gym",
        "deadline": "2026-07-15",
        "value": 45.0,
        "recurrent": False,
    }
    client.post("/expenses", json=expense)

    res = client.get("/expenses", params={"month": "2026-08"})
    assert res.status_code == 200
    assert res.json() == []


def test_list_with_month_excludes_recurring_before_it_existed(client):
    expense = {
        "description": "Rent",
        "deadline": "2026-07-15",
        "value": 1500.0,
        "recurrent": True,
    }
    client.post("/expenses", json=expense)

    res = client.get("/expenses", params={"month": "2026-06"})
    assert res.status_code == 200
    assert res.json() == []


def test_list_with_month_projects_recurring_deadline_forward(client):
    expense = {
        "description": "Rent",
        "deadline": "2026-01-31",
        "value": 1500.0,
        "recurrent": True,
    }
    client.post("/expenses", json=expense)

    # February has 28 days in 2026 (not a leap year); the 31st clamps to 28th.
    res = client.get("/expenses", params={"month": "2026-02"})
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["deadline"] == "2026-02-28"


def test_list_with_invalid_month_returns_400(client):
    res = client.get("/expenses", params={"month": "not-a-month"})
    assert res.status_code == 400


def test_list_with_out_of_range_month_returns_400_not_500(client):
    """A recurring expense whose home month sorts before '2026-13' would hit
    calendar.monthrange(2026, 13) if month weren't range-checked, raising an
    unhandled exception instead of a clean 400."""
    expense = {
        "description": "Rent",
        "deadline": "2026-01-15",
        "value": 1500.0,
        "recurrent": True,
    }
    client.post("/expenses", json=expense)

    res = client.get("/expenses", params={"month": "2026-13"})
    assert res.status_code == 400


# --- Per-month paid/due isolation -----------------------------------------


def test_set_paid_on_home_month_updates_base_record(client):
    expense = {
        "description": "Rent",
        "deadline": "2026-07-15",
        "value": 1500.0,
        "recurrent": True,
    }
    created = client.post("/expenses", json=expense).json()

    res = client.put(
        f"/expenses/{created['id']}/paid",
        params={"month": "2026-07"},
        json={"paid": True},
    )
    assert res.status_code == 200
    assert res.json()["paid"] is True
    assert client.get("/expenses").json()[0]["paid"] is True


def test_marking_one_month_paid_does_not_affect_another_month(client):
    """The core requirement from issue #10: paid/due is tracked per month."""
    expense = {
        "description": "Rent",
        "deadline": "2026-04-01",
        "value": 1500.0,
        "recurrent": True,
    }
    created = client.post("/expenses", json=expense).json()

    # Mark April (the home month) paid.
    client.put(
        f"/expenses/{created['id']}/paid",
        params={"month": "2026-04"},
        json={"paid": True},
    )

    april = client.get("/expenses", params={"month": "2026-04"}).json()
    may = client.get("/expenses", params={"month": "2026-05"}).json()
    assert april[0]["paid"] is True
    assert may[0]["paid"] is False  # May is unaffected by April's paid status.

    # Now mark May paid instead; April should remain paid and June untouched.
    client.put(
        f"/expenses/{created['id']}/paid",
        params={"month": "2026-05"},
        json={"paid": True},
    )
    april_again = client.get("/expenses", params={"month": "2026-04"}).json()
    may_again = client.get("/expenses", params={"month": "2026-05"}).json()
    june = client.get("/expenses", params={"month": "2026-06"}).json()
    assert april_again[0]["paid"] is True
    assert may_again[0]["paid"] is True
    assert june[0]["paid"] is False


def test_set_paid_for_non_recurring_other_month_is_rejected(client):
    expense = {
        "description": "Gym",
        "deadline": "2026-07-15",
        "value": 45.0,
        "recurrent": False,
    }
    created = client.post("/expenses", json=expense).json()

    res = client.put(
        f"/expenses/{created['id']}/paid",
        params={"month": "2026-08"},
        json={"paid": True},
    )
    assert res.status_code == 400


def test_set_paid_not_found(client):
    res = client.put(
        "/expenses/does-not-exist/paid",
        params={"month": "2026-07"},
        json={"paid": True},
    )
    assert res.status_code == 404


def test_set_paid_invalid_month_returns_400(client, sample_expense):
    created = client.post("/expenses", json=sample_expense).json()
    res = client.put(
        f"/expenses/{created['id']}/paid",
        params={"month": "bogus"},
        json={"paid": True},
    )
    assert res.status_code == 400


def test_paid_routes_require_authentication():
    """Without forwarded JWT claims the month-scoped paid route is 401 too."""
    from src.main import app

    unauthenticated = TestClient(app)
    res = unauthenticated.put(
        "/expenses/x/paid", params={"month": "2026-07"}, json={"paid": True}
    )
    assert res.status_code == 401


# --- Installments -------------------------------------------------------


def test_create_with_installments_success_and_roundtrips(client, sample_expense):
    expense = {
        **sample_expense,
        "installment_current": 1,
        "installment_total": 3,
    }
    res = client.post("/expenses", json=expense)
    assert res.status_code == 201
    body = res.json()
    assert body["installment_current"] == 1
    assert body["installment_total"] == 3

    fetched = client.get("/expenses").json()[0]
    assert fetched == body


def test_create_with_mismatched_installments_returns_422(client, sample_expense):
    expense = {**sample_expense, "installment_current": 5, "installment_total": 3}
    res = client.post("/expenses", json=expense)
    assert res.status_code == 422


def test_list_with_month_reflects_projected_installment_current(client):
    expense = {
        "description": "TV",
        "deadline": "2026-07-15",
        "value": 300.0,
        "recurrent": False,
        "installment_current": 1,
        "installment_total": 3,
    }
    client.post("/expenses", json=expense)

    res = client.get("/expenses", params={"month": "2026-08"})
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["installment_current"] == 2


# --- Category ----------------------------------------------------------


def test_create_with_valid_category_roundtrips(client, sample_expense):
    res = client.post("/expenses", json={**sample_expense, "category": "Food"})
    assert res.status_code == 201
    created = res.json()
    assert created["category"] == "Food"

    fetched = client.get("/expenses").json()[0]
    assert fetched["category"] == "Food"


def test_create_with_invalid_category_returns_422(client, sample_expense):
    res = client.post("/expenses", json={**sample_expense, "category": "Bogus"})
    assert res.status_code == 422


def test_create_without_category_defaults_to_null(client, sample_expense):
    res = client.post("/expenses", json=sample_expense)
    assert res.status_code == 201
    assert res.json()["category"] is None


# --- Observations --------------------------------------------------------


def test_create_with_observations_roundtrips(client, sample_expense):
    res = client.post(
        "/expenses",
        json={**sample_expense, "observations": "Pay via bank transfer, ref #123"},
    )
    assert res.status_code == 201
    created = res.json()
    assert created["observations"] == "Pay via bank transfer, ref #123"

    fetched = client.get("/expenses").json()[0]
    assert fetched["observations"] == "Pay via bank transfer, ref #123"


def test_create_without_observations_defaults_to_null(client, sample_expense):
    res = client.post("/expenses", json=sample_expense)
    assert res.status_code == 201
    assert res.json()["observations"] is None
