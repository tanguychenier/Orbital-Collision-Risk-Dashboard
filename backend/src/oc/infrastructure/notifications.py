"""Outbound notifier adapters for the alert subsystem.

Implements :class:`oc.application.ports.AlertNotifier` for three
delivery flavours:

* :class:`HttpWebhookNotifier` -- POSTs the JSON payload to a Discord-
  compatible webhook URL.
* :class:`SmtpEmailNotifier` -- sends a plaintext email via SMTP.
* :class:`CompositeNotifier` -- routes by target shape (URL vs email)
  and falls back to a logging notifier when SMTP is not configured.
"""

from __future__ import annotations

import logging
import re
import smtplib
from email.message import EmailMessage

import httpx

from oc.config import Settings

logger = logging.getLogger(__name__)


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _looks_like_email(target: str) -> bool:
    """Return ``True`` iff ``target`` looks like an email address."""
    return _EMAIL_RE.match(target.strip()) is not None


class HttpWebhookNotifier:
    """POSTs a JSON payload to a webhook URL using ``httpx.AsyncClient``."""

    def __init__(self, client: httpx.AsyncClient | None = None, timeout: float = 10.0) -> None:
        self._client = client
        self._timeout = timeout

    async def notify(
        self,
        target: str,
        subject: str,
        message: str,
        payload: dict[str, object],
    ) -> bool:
        """POST ``payload`` to ``target`` and return ``True`` on a 2xx response."""
        try:
            if self._client is not None:
                response = await self._client.post(target, json=payload)
            else:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(target, json=payload)
            ok = 200 <= response.status_code < 300
            if not ok:
                logger.warning(
                    "webhook delivery non-2xx",
                    extra={"status": response.status_code, "target": target},
                )
            return ok
        except httpx.HTTPError as exc:
            logger.warning("webhook delivery failed", extra={"error": str(exc), "target": target})
            return False


class SmtpEmailNotifier:
    """Sends an email through ``smtplib.SMTP``.

    The SMTP send is intentionally synchronous: SMTP servers are slow
    enough that adding an event loop would dominate the cost. Callers
    that care about latency should run the notifier from an executor.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def notify(
        self,
        target: str,
        subject: str,
        message: str,
        payload: dict[str, object],
    ) -> bool:
        """Send a plaintext email to ``target``. Returns ``True`` on success."""
        if self._settings.smtp_host is None:
            logger.info(
                "smtp not configured, would have emailed",
                extra={"target": target, "subject": subject},
            )
            return True
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self._settings.smtp_from_address
        msg["To"] = target
        msg.set_content(message)
        try:
            with smtplib.SMTP(self._settings.smtp_host, self._settings.smtp_port) as smtp:
                smtp.ehlo()
                if self._settings.smtp_username and self._settings.smtp_password:
                    smtp.starttls()
                    smtp.login(self._settings.smtp_username, self._settings.smtp_password)
                smtp.send_message(msg)
            return True
        except (smtplib.SMTPException, OSError) as exc:
            logger.warning("smtp delivery failed", extra={"error": str(exc), "target": target})
            return False


class CompositeNotifier:
    """Routes a delivery to the webhook or email adapter based on target shape."""

    def __init__(
        self,
        webhook: HttpWebhookNotifier,
        email: SmtpEmailNotifier,
    ) -> None:
        self._webhook = webhook
        self._email = email

    async def notify(
        self,
        target: str,
        subject: str,
        message: str,
        payload: dict[str, object],
    ) -> bool:
        """Dispatch to the email adapter if ``target`` looks like an email, else webhook."""
        if _looks_like_email(target):
            return await self._email.notify(target, subject, message, payload)
        return await self._webhook.notify(target, subject, message, payload)


def build_default_notifier(settings: Settings) -> CompositeNotifier:
    """Composition root for the default notifier wiring."""
    return CompositeNotifier(
        webhook=HttpWebhookNotifier(timeout=settings.http_timeout_seconds),
        email=SmtpEmailNotifier(settings),
    )
