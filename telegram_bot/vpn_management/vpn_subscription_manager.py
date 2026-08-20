import logging
from asyncio import run
from collections.abc import Sequence
from pprint import pprint
from typing import Any
from uuid import uuid4

from db.schemas import ProductPydantic
from db.select_methods import get_all_product_from_direction_id
# from settings.config import USER, PASSWORD
from vpn_management.vlessuiapi import XUIClient


def _validate_product(
    product: ProductPydantic,
    *,
    require_total_gb: bool,
) -> list[str]:
    """
    Проверяет наличие обязательных VLESS-параметров у продукта.

    Args:
        product: Модель продукта с параметрами VLESS-панели.
        require_total_gb: Требовать ли поле ``total_gb``. Для основного
            продукта оно обязательно, для бонусного используется отдельный
            лимит ``bonus_total_gb``.

    Returns:
        Список названий незаполненных обязательных полей. Пустой список
        означает, что валидация успешно пройдена.
    """
    logging.info(
        "Начинаем валидацию VLESS-продукта: product_id=%s, title=%r",
        product.id,
        product.title,
    )

    required_fields = [
        "base_url",
        "api_vless_token",
        "public_key",
        "short_id",
        "inbound_id",
    ]

    if require_total_gb:
        required_fields.append("total_gb")

    missing_fields = [
        field_name
        for field_name in required_fields
        if getattr(product, field_name) is None
    ]

    if missing_fields:
        logging.info(
            "Валидация VLESS-продукта не пройдена: "
            "product_id=%s, missing_fields=%s",
            product.id,
            ", ".join(missing_fields),
        )
    else:
        logging.info(
            "Валидация VLESS-продукта пройдена: product_id=%s",
            product.id,
        )

    return missing_fields


def _build_xui_client(
    *,
    product: ProductPydantic,
    username: str,
    password: str,
    verify_ssl: bool,
) -> XUIClient:
    """
    Создаёт экземпляр XUIClient для панели, заданной в продукте.

    Args:
        product: Продукт с параметрами VLESS-панели: URL, API-токен,
            public key, short ID и inbound ID.
        username: Логин для авторизации в x-ui/3x-ui панели.
        password: Пароль для авторизации в x-ui/3x-ui панели.
        verify_ssl: Нужно ли проверять SSL-сертификат панели.

    Returns:
        Настроенный экземпляр XUIClient.
    """
    logging.info(
        "Создаём XUIClient: product_id=%s, base_url=%s, inbound_id=%s",
        product.id,
        product.base_url,
        product.inbound_id,
    )

    return XUIClient(
        base_url_from_panel=product.base_url,
        username=username,
        password=password,
        api_token=product.api_vless_token,
        verify_ssl=verify_ssl,
        public_inbound_key=product.public_key,
        sid=product.short_id,
    )


def _generate_bonus_sub_id() -> str:
    """
    Генерирует subId для бонусной подписки.

    Формат: ``sub-`` + 12 символов UUID4 в hex-формате.
    Длина результата всегда равна 16 символам.

    Returns:
        Уникальный строковый subId, например ``sub-82bc4f629d97``.
    """
    sub_id = f"sub-{uuid4().hex[:12]}"

    logging.info(
        "Сгенерирован subId для бонусной подписки: sub_id=%s",
        sub_id,
    )

    return sub_id


def create_vpn_subscriptions(
    *,
    main_product: ProductPydantic,
    bonus_products: Sequence[ProductPydantic] | None = None,
    client_uuid: str,
    expire_time_sec: int,
    username: str,
    password: str,
    flow: str = "xtls-rprx-vision",
    bonus_total_gb: int = 4,
    verify_ssl: bool = True,
) -> dict[str, Any]:
    """
    Создаёт основную VLESS-подписку и добавляет к ней бонусные подписки.

    Функция не зависит от aiogram и базы данных. Вызывающий код должен
    самостоятельно получить ``main_product`` и подготовить список
    доступных ``bonus_products``.

    Если ``bonus_products`` равен ``None`` или является пустым списком,
    функция создаёт только основную VLESS-подписку.

    Args:
        main_product: Основной оплаченный продукт. Должен содержать поля:
            ``id``, ``base_url``, ``total_gb``, ``inbound_id``,
            ``api_vless_token``, ``public_key`` и ``short_id``.

        bonus_products: Список бонусных продуктов, доступность и capacity
            которых уже проверены в вызывающем модуле. Для каждого продукта
            создаётся отдельный VLESS-клиент. Если список пуст или ``None``,
            бонусные клиенты не создаются.

        client_uuid: Уникальный идентификатор основной VLESS-подписки.
            Обычно: ``str(payment_data.operation_id)``. Используется как
            ``client_uuid`` и ``email`` основного клиента.

        expire_time_sec: Срок действия подписок в формате Unix timestamp
            (секунды).

        username: Логин x-ui/3x-ui панели.

        password: Пароль x-ui/3x-ui панели.

        flow: Значение VLESS flow. По умолчанию:
            ``"xtls-rprx-vision"``.

        bonus_total_gb: Лимит трафика в ГБ для каждого бонусного клиента.
            По умолчанию: ``4``.

        verify_ssl: Проверять ли SSL-сертификат VLESS-панелей.
            По умолчанию: ``True``.

    Returns:
        Словарь с результатом:

        - ``success``: ``True``, если основная подписка создана;
        - ``message``: итоговое текстовое сообщение;
        - ``main_subscription_link``: ссылка основной подписки или ``None``;
        - ``bonus_created_count``: число созданных бонусных подписок;
        - ``bonus_links``: список бонусных subscription links;
        - ``errors``: список ошибок в формате ``dict``.

        Пример:

        .. code-block:: python

            {
                "success": True,
                "message": "VPN-подписки успешно созданы.",
                "main_subscription_link": "vless://...",
                "bonus_created_count": 2,
                "bonus_links": ["https://...", "https://..."],
                "errors": [],
            }
        Вариант вывода:
            {
                "success": True,
                "message": "Основная VPN-подписка создана. Бонусных подписок создано: 1. Ошибок: 1.",
                "main_subscription_link": "https://vpn.example.com/sub/main-user-123",
                "bonus_created_count": 1,
                "bonus_links": [
                    "https://vpn.example.com/sub/sub-82bc4f629d97",
                ],
                "errors": [
                    {
                        "stage": "bonus_subscription",
                        "product_id": 17,
                        "error": "API не вернуло subscription_link",
                    }
                ],
            }
    """
    bonus_products = bonus_products or ()

    result: dict[str, Any] = {
        "success": False,
        "message": "",
        "main_subscription_link": None,
        "bonus_created_count": 0,
        "bonus_links": [],
        "errors": [],
    }

    logging.info(
        "Начинаем создание VPN-подписок: main_product_id=%s, "
        "client_uuid=%s, bonus_products_count=%d, expire_time_sec=%s",
        main_product.id,
        client_uuid,
        len(bonus_products),
        expire_time_sec,
    )

    try:
        main_missing_fields = _validate_product(
            main_product,
            require_total_gb=True,
        )

        if main_missing_fields:
            raise ValueError(
                f"Основной продукт id={main_product.id} не содержит поля: "
                f"{', '.join(main_missing_fields)}"
            )

        main_client = _build_xui_client(
            product=main_product,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        logging.info(
            "Начинаем создание основной VLESS-подписки: "
            "product_id=%s, client_uuid=%s, inbound_id=%s, total_gb=%s",
            main_product.id,
            client_uuid,
            main_product.inbound_id,
            main_product.total_gb,
        )

        test_response = main_client.get_client_traffic_by_id(client_uuid=client_uuid)

        client_obj = test_response.get("obj")

        # if not isinstance(client_obj, list):
        #     raise RuntimeError(
        #         "x-ui API вернул некорректный ответ при проверке клиента: "
        #         f"client_uuid={client_uuid}, response={test_response!r}"
        #     )

        if client_obj or not isinstance(client_obj, list):
            logging.warning(
                "Попытка повторно создать VLESS-клиента: client_uuid=%s",
                client_uuid,
            )
            raise RuntimeError(
                f"VLESS-клиент уже существует: client_uuid={client_uuid}"
                f"client_uuid={client_uuid}, response={test_response!r}"
            )

        main_response = main_client.add_client(
            client_uuid=client_uuid,
            flow=flow,
            total_gb=main_product.total_gb,
            inbound_id=str(main_product.inbound_id),
            expiry_time=expire_time_sec,
            email=client_uuid,
        )

        main_subscription_link = main_response.get("subscription_link")

        if not main_subscription_link:
            raise RuntimeError(
                "Основная VLESS-подписка создана, "
                "но API не вернуло subscription_link"
            )

        result["main_subscription_link"] = main_subscription_link

        logging.info(
            "Основная VLESS-подписка успешно создана: "
            "product_id=%s, client_uuid=%s",
            main_product.id,
            client_uuid,
        )

    except Exception as exc:
        logging.exception(
            "Ошибка при создании основной VLESS-подписки: "
            "product_id=%s, client_uuid=%s",
            main_product.id,
            client_uuid,
        )

        result["message"] = "Не удалось создать основную VLESS-подписку."
        result["errors"].append(
            {
                "stage": "main_subscription",
                "product_id": main_product.id,
                "error": str(exc),
            }
        )

        logging.info(
            "Создание VPN-подписок завершилось ошибкой на основной подписке: "
            "main_product_id=%s, client_uuid=%s",
            main_product.id,
            client_uuid,
        )

        return result

    external_links: list[str] = []

    if not bonus_products:
        logging.info(
            "Бонусные продукты отсутствуют: main_product_id=%s, client_uuid=%s",
            main_product.id,
            client_uuid,
        )

    for index, bonus_product in enumerate(bonus_products, start=1):
        if bonus_product.id == main_product.id:
            logging.info(
                "Основной продукт пропущен в bonus_products: product_id=%s",
                main_product.id,
            )
            continue

        logging.info(
            "Начинаем обработку бонусного продукта: "
            "product_id=%s, bonus_index=%s, client_uuid=%s",
            bonus_product.id,
            index,
            client_uuid,
        )

        try:
            bonus_missing_fields = _validate_product(
                bonus_product,
                require_total_gb=False,
            )

            if bonus_missing_fields:
                raise ValueError(
                    f"Бонусный продукт id={bonus_product.id} "
                    f"не содержит поля: {', '.join(bonus_missing_fields)}"
                )

            bonus_client = _build_xui_client(
                product=bonus_product,
                username=username,
                password=password,
                verify_ssl=verify_ssl,
            )

            bonus_sub_id = None

            logging.info(
                "Начинаем создание бонусной VLESS-подписки: "
                "product_id=%s, inbound_id=%s, total_gb=%s, sub_id=%s",
                bonus_product.id,
                bonus_product.inbound_id,
                bonus_total_gb,
                bonus_sub_id,
            )

            bonus_response = bonus_client.add_client(
                client_uuid=None,
                flow=flow,
                total_gb=bonus_total_gb,
                inbound_id=str(bonus_product.inbound_id),
                expiry_time=expire_time_sec,
                email=f"PROMO_{index}_{client_uuid}",
                sub_id=bonus_sub_id,
            )

            bonus_subscription_link = bonus_response.get("subscription_link")

            if not bonus_subscription_link:
                raise RuntimeError("API не вернуло subscription_link")

            external_links.append(bonus_subscription_link)
            result["bonus_links"].append(bonus_subscription_link)
            result["bonus_created_count"] += 1

            logging.info(
                "Бонусная VLESS-подписка успешно создана: "
                "product_id=%s, client_uuid=%s, sub_id=%s",
                bonus_product.id,
                client_uuid,
                bonus_sub_id,
            )

        except Exception as exc:
            logging.exception(
                "Ошибка создания бонусной VLESS-подписки: "
                "product_id=%s, client_uuid=%s",
                bonus_product.id,
                client_uuid,
            )

            result["errors"].append(
                {
                    "stage": "bonus_subscription",
                    "product_id": bonus_product.id,
                    "error": str(exc),
                }
            )

    if external_links:
        logging.info(
            "Начинаем привязку бонусных ссылок к основной подписке: "
            "client_uuid=%s, external_links_count=%d",
            client_uuid,
            len(external_links),
        )

        try:
            main_client.add_client_external_links(
                email=client_uuid,
                subscriptions_links=external_links,
            )

            logging.info(
                "Бонусные ссылки успешно привязаны к основной подписке: "
                "client_uuid=%s, external_links_count=%d",
                client_uuid,
                len(external_links),
            )

        except Exception as exc:
            logging.exception(
                "Ошибка при привязке бонусных ссылок: client_uuid=%s",
                client_uuid,
            )

            result["errors"].append(
                {
                    "stage": "attach_external_links",
                    "product_id": main_product.id,
                    "error": str(exc),
                }
            )

    result["success"] = True

    if result["errors"]:
        result["message"] = (
            "Основная VPN-подписка создана. "
            f"Бонусных подписок создано: {result['bonus_created_count']}. "
            f"Ошибок: {len(result['errors'])}."
        )
    else:
        result["message"] = (
            "VPN-подписки успешно созданы. "
            f"Бонусных подписок добавлено: {result['bonus_created_count']}."
        )

    logging.info(
        "Создание VPN-подписок завершено: main_product_id=%s, "
        "client_uuid=%s, success=%s, bonus_created_count=%d, errors_count=%d",
        main_product.id,
        client_uuid,
        result["success"],
        result["bonus_created_count"],
        len(result["errors"]),
    )

    return result


if __name__ == "__main__":
    list_of_products = run(get_all_product_from_direction_id(group_id=1))
    client_uuid_from_payment = str("SUKANAHUI10-jansdkjnjkdnkjs")

    vpn_result = create_vpn_subscriptions(
        main_product=list_of_products[0],
        bonus_products=list_of_products,
        client_uuid=client_uuid_from_payment,
        expire_time_sec=1772620800000,
        username="USER",
        password="PASSWORD",
    )
    print()
    pprint(vpn_result)

