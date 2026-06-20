"""End-to-end smoke test against the local stack.

Exercises create -> list -> edit -> delete through the backend Lambda endpoint
(the API Gateway proxy -> RIE -> FastAPI handler) backed by DynamoDB Local.
Standard library only, so it runs from a clean checkout and in CI.

Usage:
    python local/smoke_test.py [base_url]   # default http://localhost:5000
"""

import json
import sys
import urllib.error
import urllib.request

BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000").rstrip("/")


def request(method: str, path: str, body: dict | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return exc.code, (json.loads(raw) if raw else None)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"  ok: {message}")


def main() -> int:
    print(f"Smoke test against {BASE_URL}")

    # Clean slate is not assumed; just verify CRUD on a new item.
    status, listing = request("GET", "/expenses")
    check(status == 200, "GET /expenses returns 200")
    check(isinstance(listing, list), "listing is an array")
    start_count = len(listing)

    new = {
        "description": "Smoke test expense",
        "deadline": "2026-12-31",
        "value": 42.5,
        "recurrent": False,
    }
    status, created = request("POST", "/expenses", new)
    check(status == 201, "POST /expenses returns 201")
    check(bool(created.get("id")), "created expense has an id")
    expense_id = created["id"]

    status, listing = request("GET", "/expenses")
    check(len(listing) == start_count + 1, "list grew by one")

    edit = {**new, "description": "Smoke test edited", "value": 99.99}
    status, updated = request("PUT", f"/expenses/{expense_id}", edit)
    check(status == 200, "PUT /expenses/{id} returns 200")
    check(updated["description"] == "Smoke test edited", "update persisted")
    check(updated["value"] == 99.99, "updated value persisted")
    check(updated["id"] == expense_id, "id is stable across update")

    status, _ = request("DELETE", f"/expenses/{expense_id}")
    check(status == 204, "DELETE /expenses/{id} returns 204")

    status, _ = request("DELETE", f"/expenses/{expense_id}")
    check(status == 404, "deleting again returns 404")

    status, listing = request("GET", "/expenses")
    check(len(listing) == start_count, "list back to starting size")

    print("\nSMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print(f"\nSMOKE TEST FAILED: {exc}")
        sys.exit(1)
