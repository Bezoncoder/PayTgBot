import logging

from aiohttp import web
from aiogram.types import Update
from settings.config import bot, dp
from pathlib import Path

async def handle_webhook(request: web.Request):
    try:
        update = Update.model_validate(await request.json(), context={"bot": bot})
        await dp.feed_update(bot, update)
        return web.Response(status=200)
    except Exception as e:
        print(f"Webhook error: {e}")
        return web.Response(status=500)

async def home_page(request: web.Request) -> web.Response:
    """
    Обработчик для отображения главной страницы из файла source/templates/index.html.
    """
    file_path = Path("source/templates/index.html")

    if not file_path.exists():
        raise web.HTTPNotFound(text="Файл source/templates/index.html не найден")

    html_content = file_path.read_text(encoding="utf-8")
    return web.Response(text=html_content, content_type="text/html")

async def payment_success(request: web.Request) -> web.Response:
    try:
        operation_id = request.query.get("operation_id")
        successful_raw = request.query.get("successful")

        if operation_id is None or successful_raw is None:
            return web.json_response(
                {"success": False, "message": "operation_id and successful are required"},
                status=400
            )

        successful = successful_raw

        if not successful:

            return web.json_response({
                "success": False,
                "message": "Payment not confirmed",
                "operation_id": operation_id
            })


        return web.Response(status=200)

    except Exception:
        logging.exception("payment_success error")
        return web.Response(status=500)
