"""Direct tests for the generic DynamoDB repository (moto-backed)."""


class _PagingTable:
    """Stub table whose scan paginates via LastEvaluatedKey."""

    def __init__(self):
        self.pages = [
            {"Items": [{"id": "page-1"}], "LastEvaluatedKey": {"id": "page-1"}},
            {"Items": [{"id": "page-2"}]},
        ]
        self.start_keys = []

    def scan(self, **kwargs):
        if "ExclusiveStartKey" in kwargs:
            self.start_keys.append(kwargs["ExclusiveStartKey"])
        return self.pages[len(self.start_keys)]


def _item(**overrides):
    base = {
        "id": "abc-123",
        "description": "Rent",
        "deadline": "2026-08-01",
        "value": 1500.0,
        "recurrent": True,
    }
    base.update(overrides)
    return base


def test_save_and_get(repository):
    item = _item()
    repository.save(item)
    fetched = repository.get("abc-123")
    assert fetched == item


def test_get_missing_returns_none(repository):
    assert repository.get("nope") is None


def test_list(repository):
    repository.save(_item(id="a"))
    repository.save(_item(id="b"))
    ids = {row["id"] for row in repository.list()}
    assert ids == {"a", "b"}


def test_update_overwrites(repository):
    repository.save(_item())
    repository.update("abc-123", _item(description="Changed", value=10.25))
    fetched = repository.get("abc-123")
    assert fetched["description"] == "Changed"
    assert fetched["value"] == 10.25


def test_value_roundtrips_as_number(repository):
    """Floats are stored as Decimal but come back as native numbers."""
    repository.save(_item(value=42.75))
    assert repository.get("abc-123")["value"] == 42.75
    repository.save(_item(id="whole", value=100.0))
    # Integral values come back as int, not Decimal.
    assert repository.get("whole")["value"] == 100


def test_delete(repository):
    repository.save(_item())
    assert repository.delete("abc-123") is True
    assert repository.get("abc-123") is None


def test_delete_missing_returns_false(repository):
    assert repository.delete("nope") is False


def test_list_follows_scan_pagination(repository):
    table = _PagingTable()
    repository.table = table
    ids = [row["id"] for row in repository.list()]
    assert ids == ["page-1", "page-2"]
    assert table.start_keys == [{"id": "page-1"}]
