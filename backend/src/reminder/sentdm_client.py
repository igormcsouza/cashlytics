"""Sent.dm WhatsApp client, wrapped behind our own narrow interface.

The reminder domain calls :func:`send_reminder` only — it never imports
``sent_dm`` directly, the same way ``services.py`` elsewhere never imports
``boto3`` directly and instead depends on the ``Repository`` protocol. This
keeps the third-party SDK an implementation detail that can be swapped
without touching business logic.
"""

from functools import lru_cache

from sent_dm import Sent, SentError

from src.core.config import sentdm_api_key, sentdm_template_id
from src.reminder.exceptions import WhatsAppSendError


@lru_cache(maxsize=1)
def _get_client() -> Sent:
    """Sent.dm SDK client, initialized once and cached (cold-start friendly)."""
    return Sent(api_key=sentdm_api_key())


def send_reminder(to: str, message: str) -> str:
    """Send the daily reminder message to ``to`` via the Sent.dm WhatsApp channel.

    Returns the provider's ``message_id``. Raises :class:`WhatsAppSendError` on
    any failure — network, auth, or a rejected template — since callers only
    need to know the send didn't succeed, not the SDK's internal exception
    hierarchy (``SentError`` is the base of every exception the SDK raises,
    e.g. ``AuthenticationError``, ``RateLimitError``, ``APIConnectionError``).
    """
    try:
        response = _get_client().messages.send(
            to=[to],
            channel=["whatsapp"],
            template={
                "id": sentdm_template_id(),
                "name": "expense_reminder",
                "parameters": {"message": message},
            },
        )
    except SentError as exc:
        raise WhatsAppSendError(str(exc)) from exc

    return response.data.recipients[0].message_id
