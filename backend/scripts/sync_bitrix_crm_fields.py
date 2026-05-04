#!/usr/bin/env python3
"""Синхронизация CRM-полей Bitrix24 для маршрутизации опросников."""

import argparse
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from loguru import logger

from app.core.database import async_session_maker
from app.services.bitrix_crm_fields import sync_bitrix_deal_fields


MOSCOW_TZ = ZoneInfo("Europe/Moscow")


async def sync_once() -> dict:
    async with async_session_maker() as db:
        return await sync_bitrix_deal_fields(db)


def seconds_until_next_midnight() -> float:
    now = datetime.now(MOSCOW_TZ)
    next_midnight = (now + timedelta(days=1)).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    return max(1.0, (next_midnight - now).total_seconds())


async def run_periodic_sync() -> None:
    logger.info("Запуск worker синхронизации CRM-полей Bitrix24 (ежедневно в 00:00 Europe/Moscow)")
    while True:
        sleep_seconds = seconds_until_next_midnight()
        logger.info(f"Следующая синхронизация CRM-полей через {round(sleep_seconds)} секунд")
        await asyncio.sleep(sleep_seconds)
        try:
            await sync_once()
        except Exception as exc:
            logger.error(f"Ошибка синхронизации CRM-полей Bitrix24: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Выполнить одну синхронизацию и завершиться")
    args = parser.parse_args()

    if args.once:
        result = asyncio.run(sync_once())
        print(result)
        return

    asyncio.run(run_periodic_sync())


if __name__ == "__main__":
    main()
