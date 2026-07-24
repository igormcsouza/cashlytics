"""Domain exceptions for the reminder domain."""


class ReminderSendError(Exception):
    """Sending the reminder message via Sent.dm failed."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Failed to send reminder: {reason}")
