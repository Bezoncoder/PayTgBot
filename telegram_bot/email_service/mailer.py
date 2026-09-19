from __future__ import annotations

import re
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any

import aiosmtplib
from aiosmtplib import SMTPResponse
from email_validator import EmailNotValidError, validate_email

from email_service.models import EmailSendResult


class Mailer:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        from_email: str,
        from_name: str,
        use_tls: bool = True,
        start_tls: bool | None = None,
        timeout: float = 15,
    ) -> None:
        if use_tls and start_tls:
            raise ValueError(
                "use_tls и start_tls нельзя включать одновременно. "
                "Для порта 465 используйте use_tls=True. "
                "Для порта 587 используйте use_tls=False, start_tls=True."
            )

        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from_email = self._validate_email(
            from_email,
            field_name="from_email",
        )
        self._from_name = self._validate_header_value(
            from_name,
            field_name="from_name",
        )
        self._use_tls = use_tls
        self._start_tls = start_tls
        self._timeout = timeout

    async def send(
        self,
        *,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> EmailSendResult:
        validated_to_email = self._validate_email(
            to_email,
            field_name="to_email",
        )
        validated_subject = self._validate_header_value(
            subject,
            field_name="subject",
        )

        message = EmailMessage()
        message["From"] = f"{self._from_name} <{self._from_email}>"
        message["To"] = validated_to_email
        message["Subject"] = validated_subject

        message.set_content(text_body)

        if html_body is not None:
            message.add_alternative(html_body, subtype="html")

        result = await aiosmtplib.send(
            message,
            hostname=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
            use_tls=self._use_tls,
            start_tls=self._start_tls,
            timeout=self._timeout,
        )

        refused_recipients, smtp_response = self._parse_smtp_result(result)
        smtp_code, smtp_response_text = self._parse_smtp_response(smtp_response)

        return EmailSendResult(
            status=self._get_status(
                refused_recipients=refused_recipients,
                smtp_code=smtp_code,
                smtp_response=smtp_response_text,
            ),
            smtp_code=smtp_code,
            smtp_response=smtp_response_text,
            smtp_queue_id=self._extract_queue_id(smtp_response_text),
            refused_recipients=refused_recipients,
        )

    @staticmethod
    def _validate_header_value(
        value: str,
        *,
        field_name: str,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} должен быть строкой.")

        if not value.strip():
            raise ValueError(f"{field_name} не должен быть пустым.")

        if "\r" in value or "\n" in value or "\x00" in value:
            raise ValueError(
                f"{field_name} содержит недопустимые символы "
                r"\r, \n или \x00."
            )

        return value.strip()

    @classmethod
    def _validate_email(
        cls,
        value: str,
        *,
        field_name: str,
    ) -> str:
        raw_email = cls._validate_header_value(
            value,
            field_name=field_name,
        )

        try:
            result = validate_email(
                raw_email,
                check_deliverability=False,
            )
        except EmailNotValidError as exc:
            raise ValueError(
                f"{field_name} содержит некорректный email: {exc}"
            ) from exc

        return result.normalized

    @staticmethod
    def _parse_smtp_result(
        result: Any,
    ) -> tuple[dict[str, Any], Any]:
        if not isinstance(result, tuple) or len(result) != 2:
            return {}, result

        refused_recipients, smtp_response = result

        if not isinstance(refused_recipients, dict):
            refused_recipients = {}

        return refused_recipients, smtp_response

    @staticmethod
    def _parse_smtp_response(
        smtp_response: Any,
    ) -> tuple[int | None, str | None]:
        if smtp_response is None:
            return None, None

        if isinstance(smtp_response, SMTPResponse):
            return (
                smtp_response.code,
                Mailer._normalize_smtp_response(smtp_response.message),
            )

        code = getattr(smtp_response, "code", None)
        message = getattr(smtp_response, "message", None)

        if isinstance(code, int) and message is not None:
            return code, Mailer._normalize_smtp_response(message)

        return None, Mailer._normalize_smtp_response(smtp_response)

    @staticmethod
    def _normalize_smtp_response(value: Any) -> str | None:
        if value is None:
            return None

        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")

        return str(value)

    @staticmethod
    def _extract_queue_id(smtp_response: str | None) -> str | None:
        if not smtp_response:
            return None

        match = re.search(
            r"\bqueued\s+as\s+([A-Za-z0-9._-]+)\b",
            smtp_response,
            flags=re.IGNORECASE,
        )

        return match.group(1) if match else None

    @staticmethod
    def _get_status(
        *,
        refused_recipients: dict[str, Any],
        smtp_code: int | None,
        smtp_response: str | None,
    ) -> str:
        if refused_recipients:
            return "failed"

        if smtp_code is not None:
            if 200 <= smtp_code < 300:
                return "accepted"

            if 400 <= smtp_code < 600:
                return "failed"

            return "unknown"

        if not smtp_response:
            return "unknown"

        normalized_response = smtp_response.strip()

        if (
            normalized_response.startswith("2.")
            or normalized_response.startswith("250")
            or normalized_response.lower().startswith("ok")
        ):
            return "accepted"

        if re.match(r"^(4|5)\d{2}\b", normalized_response):
            return "failed"

        return "unknown"