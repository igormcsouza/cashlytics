"""Tests for the Sent.dm client wrapper — the SDK itself is faked, no network."""

import pytest
from sent_dm import SentError

from src.reminder import sentdm_client
from src.reminder.exceptions import ReminderSendError


class FakeRecipient:
    def __init__(self, message_id):
        self.message_id = message_id


class FakeData:
    def __init__(self, message_id):
        self.recipients = [FakeRecipient(message_id)]


class FakeResponse:
    def __init__(self, message_id):
        self.data = FakeData(message_id)


class FakeMessages:
    def __init__(self, response=None, error=None):
        self._response = response
        self._error = error
        self.calls: list[dict] = []

    def send(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return self._response


class FakeSentClient:
    def __init__(self, messages: FakeMessages):
        self.messages = messages


@pytest.fixture(autouse=True)
def clear_client_cache(monkeypatch):
    monkeypatch.setenv("SENTDM_API_KEY", "test-key")
    sentdm_client._get_client.cache_clear()
    yield
    sentdm_client._get_client.cache_clear()


def test_send_reminder_returns_message_id(monkeypatch):
    fake_messages = FakeMessages(response=FakeResponse("msg-1"))
    monkeypatch.setattr(
        sentdm_client, "Sent", lambda api_key: FakeSentClient(fake_messages)
    )

    message_id = sentdm_client.send_reminder("+15550001111", "hello")

    assert message_id == "msg-1"
    call = fake_messages.calls[0]
    assert call["to"] == ["+15550001111"]
    assert call["channel"] == ["sms"]
    assert call["text"] == "hello"


def test_send_reminder_wraps_sdk_error(monkeypatch):
    fake_messages = FakeMessages(error=SentError("boom"))
    monkeypatch.setattr(
        sentdm_client, "Sent", lambda api_key: FakeSentClient(fake_messages)
    )

    with pytest.raises(ReminderSendError):
        sentdm_client.send_reminder("+15550001111", "hello")
