from __future__ import annotations

import asyncio
import imaplib
import socket
import ssl
from email import policy
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.parser import BytesParser

from email_service.models import IncomingEmail


class InboxClient:
    _MAX_EMAIL_SIZE = 5 * 1024 * 1024
    _MAX_BODY_SIZE = 1 * 1024 * 1024

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        mailbox: str = "INBOX",
        timeout: float = 15,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._mailbox = mailbox
        self._timeout = timeout

    async def get_unseen(self) -> list[IncomingEmail]:
        """
        Асинхронная оболочка вокруг синхронного imaplib.
        Не блокирует event loop FastAPI, aiogram или asyncio-приложения.
        """
        return await asyncio.to_thread(self._get_unseen_sync)

    def _get_unseen_sync(self) -> list[IncomingEmail]:
        context = ssl.create_default_context()

        with imaplib.IMAP4_SSL(
            host=self._host,
            port=self._port,
            ssl_context=context,
            timeout=self._timeout,
        ) as client:
            self._expect_ok(
                client.login(self._username, self._password),
                action="IMAP login",
            )

            try:
                self._expect_ok(
                    client.select(self._mailbox, readonly=True),
                    action=f"select mailbox {self._mailbox!r}",
                )

                status, data = client.uid("SEARCH", None, "UNSEEN")

                self._expect_ok(
                    (status, data),
                    action="search unread messages",
                )

                if not data or not data[0]:
                    return []

                messages: list[IncomingEmail] = []

                for raw_uid in data[0].split():
                    uid = raw_uid.decode("ascii", errors="replace")
                    message = self._fetch_message(client, uid)

                    if message is not None:
                        messages.append(message)

                return messages

            finally:
                try:
                    client.logout()
                except (imaplib.IMAP4.error, OSError, socket.error):
                    pass

    def _fetch_message(
        self,
        client: imaplib.IMAP4_SSL,
        uid: str,
    ) -> IncomingEmail | None:
        status, data = client.uid(
            "FETCH",
            uid,
            "(RFC822.SIZE BODY.PEEK[])",
        )

        self._expect_ok(
            (status, data),
            action=f"fetch message UID={uid}",
        )

        raw_email: bytes | None = None
        declared_size: int | None = None

        for item in data:
            if not isinstance(item, tuple):
                continue

            metadata, payload = item

            if isinstance(metadata, bytes):
                declared_size = self._extract_rfc822_size(metadata)

            if isinstance(payload, bytes):
                raw_email = payload

        if raw_email is None:
            return None

        if declared_size is not None and declared_size > self._MAX_EMAIL_SIZE:
            return None

        if len(raw_email) > self._MAX_EMAIL_SIZE:
            return None

        parsed_message = BytesParser(
            policy=policy.default,
        ).parsebytes(raw_email)

        return IncomingEmail(
            uid=uid,
            message_id=self._get_header(parsed_message, "Message-ID"),
            from_email=self._get_header(parsed_message, "From"),
            to_email=self._get_header(parsed_message, "To"),
            subject=self._get_header(parsed_message, "Subject") or "",
            text_body=self._get_body(
                parsed_message,
                content_type="text/plain",
            ),
            html_body=self._get_body(
                parsed_message,
                content_type="text/html",
            ),
        )

    @staticmethod
    def _expect_ok(
        result: tuple[str, list[object]],
        *,
        action: str,
    ) -> None:
        status, data = result

        if status == "OK":
            return

        details = b" ".join(
            item
            for item in data
            if isinstance(item, bytes)
        ).decode("utf-8", errors="replace")

        raise RuntimeError(
            f"IMAP operation failed: {action}. "
            f"Status={status}. Response={details}"
        )

    @staticmethod
    def _extract_rfc822_size(metadata: bytes) -> int | None:
        match = re.search(rb"RFC822\.SIZE\s+(\d+)", metadata)

        if match is None:
            return None

        return int(match.group(1))

    @staticmethod
    def _get_header(
        message: EmailMessage,
        name: str,
    ) -> str | None:
        raw_value = message.get(name)

        if raw_value is None:
            return None

        try:
            return str(make_header(decode_header(str(raw_value)))).strip()
        except (UnicodeDecodeError, ValueError):
            return str(raw_value).strip()

    def _get_body(
        self,
        message: EmailMessage,
        *,
        content_type: str,
    ) -> str | None:
        """
        Возвращает первую не-вложенную MIME-часть нужного типа.
        """
        for part in message.walk():
            if part.get_content_maintype() != "text":
                continue

            if part.get_content_type() != content_type:
                continue

            if part.get_content_disposition() == "attachment":
                continue

            try:
                body = part.get_content()
            except (LookupError, UnicodeDecodeError):
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="replace")

            if not isinstance(body, str):
                body = str(body)

            return body[:self._MAX_BODY_SIZE]

        return None