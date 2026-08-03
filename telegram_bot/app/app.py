from aiohttp import web
from aiogram.types import Update
from settings.config import bot, dp
from pathlib import Path

async def handle_webhook(request: web.Request):
    try:
        update = Update(**await request.json())
        await dp.feed_update(bot, update)
        return web.Response(status=200)
    except Exception as e:
        # logger.error(f"Ошибка при обработке вебхука: {e}")
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


async def robokassa_result(request: web.Request) -> web.Response:
    """
    Обработчик для отображения главной страницы из файла source/templates/index.html.
    """
    file_path = Path("source/templates/index.html")

    if not file_path.exists():
        raise web.HTTPNotFound(text="Файл source/templates/index.html не найден")

    html_content = file_path.read_text(encoding="utf-8")
    return web.Response(text=html_content, content_type="text/html")

async def robokassa_fail(request: web.Request) -> web.Response:
    """
    Обработчик для отображения главной страницы из файла source/templates/index.html.
    """
    file_path = Path("source/templates/index.html")

    if not file_path.exists():
        raise web.HTTPNotFound(text="Файл source/templates/index.html не найден")

    html_content = file_path.read_text(encoding="utf-8")
    return web.Response(text=html_content, content_type="text/html")