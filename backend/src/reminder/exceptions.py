"""Domain exceptions for the reminder domain."""


class WhatsAppSendError(Exception):
    """Sending the reminder WhatsApp message via Sent.dm failed."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Failed to send WhatsApp reminder: {reason}")
