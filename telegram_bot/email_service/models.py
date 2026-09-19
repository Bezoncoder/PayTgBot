from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EmailSendResult:
    status: str
    smtp_code: int | None
    smtp_response: str | None
    smtp_queue_id: str | None
    refused_recipients: dict[str, Any]


@dataclass(frozen=True)
class IncomingEmail:
    uid: str
    message_id: str | None
    from_email: str | None
    to_email: str | None
    subject: str
    text_body: str | None
    html_body: str | None