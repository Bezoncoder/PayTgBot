import logging

from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import connection
from db.schemas import (
    ProductStatisticsPydantic,
    UsersStatisticsPydantic,
)


USERS_STATISTICS_SQL = text("""
    SELECT
        COUNT(*) AS all_users,

        COUNT(*) FILTER (
            WHERE u.created_at >= date_trunc('month', CURRENT_DATE)
              AND u.created_at < date_trunc('month', CURRENT_DATE)
                                 + INTERVAL '1 month'
        ) AS new_users_this_month,

        COUNT(DISTINCT u.id) FILTER (
            WHERE EXISTS (
                SELECT 1
                FROM enrollments AS e
                WHERE e.user_id = u.id
                  AND e.active IS TRUE
            )
        ) AS active_users,

        COUNT(DISTINCT u.id) FILTER (
            WHERE (
                SELECT COUNT(*)
                FROM enrollments AS e
                WHERE e.user_id = u.id
            ) >= 2
        ) AS users_with_two_or_more_purchases

    FROM users AS u
""")

from sqlalchemy import text


PRODUCTS_STATISTICS_SQL = text("""
    SELECT
        f.title AS stream_title,
        g.tariffs_purchases_at_last_month AS purchases_last_month,
        f.tariffs_purchases_at_this_month AS purchases_this_month

    FROM (
        SELECT
            s.title,
            SUM(t.count) AS tariffs_purchases_at_this_month

        FROM (
            SELECT
                p.stream_id,
                COUNT(p.id) AS count

            FROM payments AS p

            WHERE DATE_PART(
                'month',
                CAST(p.created_at AS date)
            ) = DATE_PART(
                'month',
                CURRENT_DATE
            )
            AND p.status = 'CONFIRMED'

            GROUP BY p.stream_id
        ) AS t

        JOIN streams AS s
            ON t.stream_id = s.id

        GROUP BY s.title
    ) AS f

    JOIN (
        SELECT
            s.title,
            SUM(t.count) AS tariffs_purchases_at_last_month

        FROM (
            SELECT
                p.stream_id,
                COUNT(p.id) AS count

            FROM payments AS p

            WHERE DATE_PART(
                'month',
                CAST(p.created_at AS date)
            ) = DATE_PART(
                'month',
                CURRENT_DATE - INTERVAL '1 month'
            )
            AND p.status = 'CONFIRMED'

            GROUP BY p.stream_id
        ) AS t

        JOIN streams AS s
            ON t.stream_id = s.id

        GROUP BY s.title
    ) AS g
        ON f.title = g.title

    ORDER BY
        f.tariffs_purchases_at_this_month DESC,
        f.title
""")

@connection
async def get_users_statistics(
    session: AsyncSession,
) -> UsersStatisticsPydantic | None:
    """
    Возвращает общую статистику пользователей:

    - all_users: общее количество пользователей;
    - new_users_this_month: зарегистрированы в текущем месяце;
    - active_users: имеют хотя бы одну активную подписку;
    - users_with_two_or_more_purchases: имеют две или более записи Enrollment.
    """
    try:
        logging.info("Запрашиваем статистику пользователей")

        result = await session.execute(USERS_STATISTICS_SQL)
        row = result.mappings().one_or_none()

        if row is None:
            logging.warning(
                "Статистика пользователей не получена: SQL-запрос не вернул строку"
            )
            return None

        statistics = UsersStatisticsPydantic.model_validate(dict(row))

        logging.info(
            "Статистика пользователей получена: "
            "all_users=%s, new_users_this_month=%s, "
            "active_users=%s, users_with_two_or_more_purchases=%s",
            statistics.all_users,
            statistics.new_users_this_month,
            statistics.active_users,
            statistics.users_with_two_or_more_purchases,
        )

        return statistics

    except ValidationError:
        logging.exception(
            "Ошибка валидации Pydantic при формировании статистики пользователей"
        )
        return None

    except SQLAlchemyError:
        logging.exception(
            "Ошибка SQLAlchemy при получении статистики пользователей"
        )
        return None

    except Exception:
        logging.exception(
            "Непредвиденная ошибка при получении статистики пользователей"
        )
        return None


@connection
async def get_products_statistics(
    session: AsyncSession,
) -> list[ProductStatisticsPydantic] | None:
    """
    Возвращает статистику покупок по потокам/тарифам:

    - stream_title: название тарифа/потока;
    - purchases_last_month: число CONFIRMED оплат за прошлый месяц;
    - purchases_this_month: число CONFIRMED оплат за текущий месяц.
    """
    try:
        logging.info("Запрашиваем статистику покупок по тарифам")

        result = await session.execute(PRODUCTS_STATISTICS_SQL)
        rows = result.mappings().all()

        if not rows:
            logging.info(
                "Статистика покупок по тарифам не найдена: таблица streams пуста"
            )
            return None

        statistics = [
            ProductStatisticsPydantic.model_validate(dict(row))
            for row in rows
        ]

        logging.info(
            "Статистика покупок по тарифам получена: количество тарифов=%s",
            len(statistics),
        )

        return statistics

    except ValidationError:
        logging.exception(
            "Ошибка валидации Pydantic при формировании статистики по тарифам"
        )
        return None

    except SQLAlchemyError:
        logging.exception(
            "Ошибка SQLAlchemy при получении статистики покупок по тарифам"
        )
        return None

    except Exception:
        logging.exception(
            "Непредвиденная ошибка при получении статистики покупок по тарифам"
        )
        return None