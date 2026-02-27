import os
from asyncio import run
from db.select_methods import get_pass


async def get_creds(
    tg_user_id: str,
    start_page_url: str | None = None,
    *,
    product_title: str | None = None,
) -> str:
    selected_vars = {
        "🌬️ Airflow": ["AIRFLOW_USERNAME", "AIRFLOW_PASSWORD"],
        "🪣 MinIO (S3)": ["MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD"],
        "🦄 Kafka": ["KAFKA_LOGIN", "KAFKA_PASSWORD"],
        "🐘 Postgres": ["POSTGRES_USER", "POSTGRES_PASSWORD"],
        "📊 ClickHouse": ["CLICKHOUSE_USER", "CLICKHOUSE_PASSWORD"],
    }

    product_key = (product_title or "").lower()
    start_page_name = product_title or "InfraSharing"
    start_page_link = start_page_url or "http://start.infrasharing.local"

    message_lines = [
        "<b>🏠 Главная страница со всеми сервисами:</b>",
        f'<a href="{start_page_link}">{start_page_name}</a>',
        "",
        "📌 Подключение к БД и сервисам описано на странице.",
        "— — — — — — — — — — — —",
        "<b>⚙️ Логины / Пароли:</b>\n",
    ]

    for title, (login_key, password_key) in selected_vars.items():
        login = os.getenv(login_key, "❌ not set")
        password = os.getenv(password_key, "❌ not set")
        message_lines.append(
            f"<b>{title}</b>: <code>{login}</code> / <code>{password}</code>"
        )

    tg_id = int(tg_user_id)
    vscode_password = await get_pass(tg_id=tg_id)

    message_lines.append("— — — — — — — — — — — —")
    message_lines.append(
        f"🧑‍💻 <b>VS Code:</b> <code>{tg_id}</code> / <code>{vscode_password}</code>"
    )

    message_lines.append(
        f'📊 <b>Metabase:</b> <code>{os.getenv("METABASE_LOGIN", "❌ not set")}</code> / <code>{os.getenv("METABASE_PASS", "❌ not set")}</code>'
    )

    if "bootcamp" in product_key:
        confluence_link = os.getenv("CONFLUENCE_LINK")
        message_lines.append("— — — — — — — — — — — —")
        message_lines.append(
            f'🌀 <b>JIRA:</b> <code>{tg_id}</code> / <code>{os.getenv("JIRA_PASS", "❌ not set")}</code>'
        )
        if confluence_link:
            message_lines.append(
                f'📘 <b>Confluence:</b> <a href="{confluence_link}">Открыть Confluence</a>'
            )
        else:
            message_lines.append('📘 <b>Confluence:</b> ссылка не настроена')

    message_lines.append("— — — — — — — — — — — —")

    return "\n".join(message_lines)


# Пример использования
if __name__ == "__main__":
    run(get_creds(tg_user_id='5866726660'))
