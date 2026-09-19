from __future__ import annotations

from asyncio import run
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from email_service.models import EmailSendResult
from email_service.mailer import Mailer

SMTP_HOST="mail.quantumturbovpn.com"
SMTP_PORT=465
SMTP_USERNAME="support@quantumturbovpn.com"
SMTP_PASSWORD="%rx%kfo%h8H&h"
SMTP_FROM_EMAIL="support@quantumturbovpn.com"
SMTP_FROM_NAME="Quantum Turbo VPN"

TEMPLATES_DIR = Path(__file__).parent / "templates"

template_environment = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_template(
    template_name: str,
    **context: object,
) -> str:
    template = template_environment.get_template(template_name)
    return template.render(**context)


class EmailSender:
        def __init__(self, mailer: Mailer) -> None:
            self._mailer = mailer

        async def send_account_created(
                self,
                *,
                to_email: str,
                login: str,
                password: str,
                vpn_subscription_url: str,
                user_name: str | None = None,
        ) -> EmailSendResult:


            html_body = render_template(
                "account_created.html",
                user_name=user_name,
                login=login,
                password=password,
                vpn_subscription_url=vpn_subscription_url,
            )

            greeting = f", {user_name}" if user_name else ""

            text_body = (
                f"Здравствуйте{greeting}.\n\n"
                "Для вас создан аккаунт QuantumTurbo VPN.\n\n"
                "ДАННЫЕ АККАУНТА\n"
                f"Ваш логин: {login}\n"
                f"Ваш пароль: {password}\n\n"
                "VPN-ПОДПИСКА\n"
                f"{vpn_subscription_url}\n\n"
                "Откройте ссылку в VPN-клиенте или добавьте её вручную "
                "в настройках подписки.\n\n"
                "Если вы не ожидали это письмо, обратитесь в поддержку: "
                "support@quantumturbovpn.com"
            )

            return await self._mailer.send(
                to_email=to_email,
                subject="Данные аккаунта и VPN-подписка — QuantumTurbo VPN",
                text_body=text_body,
                html_body=html_body,
            )

async def send_test_email() -> None:
    mailer = Mailer(
                host=SMTP_HOST,
                port=SMTP_PORT,
                username=SMTP_USERNAME,
                password=SMTP_PASSWORD,
                from_email=SMTP_FROM_EMAIL,
                from_name=SMTP_FROM_NAME,
            )

    email_sender = EmailSender(mailer)

    result = await email_sender.send_account_created(
        
        to_email="bezoncoder@gmail.com",
        user_name="Иван",
        login="ivan@example.com",
        password="TEMPORARY_PASSWORD",
        vpn_subscription_url=(
            f"https://your-vpn-panel.example/sub/"
            f"INDIVIDUAL_SUBSCRIPTION_TOKEN"
        ),
    )

    print(f"Статус: {result.status}")
    print(f"SMTP-ответ: {result.smtp_response}")
    print(f"Queue ID: {result.smtp_queue_id}")


if __name__ == "__main__":
    run(send_test_email())


