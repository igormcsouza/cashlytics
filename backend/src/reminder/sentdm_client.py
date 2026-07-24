"""Sent.dm client, wrapped behind our own narrow interface.

The reminder domain calls :func:`send_reminder` only — it never imports
``sent_dm`` directly, the same way ``services.py`` elsewhere never imports
``boto3`` directly and instead depends on the ``Repository`` protocol. This
keeps the third-party SDK an implementation detail that can be swapped
without touching business logic.

Sends over SMS for now, not WhatsApp: WhatsApp requires every
business-initiated message to use a Meta-approved template (regardless of
category — marketing, utility, or authentication), which needs a full Meta
Business Portfolio link. SMS templates need none of that — no approval step,
usable immediately after creation — just a much lighter version of the same
template mechanism (Sent.dm requires a template for every channel, SMS
included; there's no way to send arbitrary free text with no template at
all). Swapping back to WhatsApp later is just a different template id.
"""

from functools import lru_cache

from sent_dm import Sent, SentError

from src.core.config import sentdm_api_key, sentdm_template_id
from src.reminder.exceptions import ReminderSendError


@lru_cache(maxsize=1)
def _get_client() -> Sent:
    """Sent.dm SDK client, initialized once and cached (cold-start friendly)."""
    return Sent(api_key=sentdm_api_key())


def send_reminder(to: str, message: str) -> str:
    """Send the daily reminder message to ``to`` via SMS.

    Returns the provider's ``message_id``. Raises :class:`ReminderSendError` on
    any failure — network, auth, an invalid/rejected template, carrier
    rejection — since callers only need to know the send didn't succeed, not
    the SDK's internal exception hierarchy (``SentError`` is the base of every
    exception the SDK raises, e.g. ``AuthenticationError``, ``RateLimitError``,
    ``APIConnectionError``).
    """
    try:
        response = _get_client().messages.send(
            to=[to],
            channel=["sms"],
            template={
                "id": sentdm_template_id(),
                "parameters": {"message": message},
            },
        )
    except SentError as exc:
        raise ReminderSendError(str(exc)) from exc

    return response.data.recipients[0].message_id
