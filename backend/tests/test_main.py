"""Tests for the app-level routes in ``src.main``."""


def test_health_route(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
