#!/usr/bin/env python3
"""
Разовый backfill для заполнения вкладок doctor portal по данным Bitrix24.
"""

import argparse
import asyncio

from loguru import logger
from sqlalchemy import select

from app.core.database import async_session_maker
from app.models import SurveySession
from app.services.bitrix24 import Bitrix24Client


async def backfill_clinic_buckets(batch_size: int = 100, only_missing: bool = False) -> dict[str, int]:
    stats = {
        "processed": 0,
        "updated": 0,
        "routed_to_test": 0,
        "errors": 0,
    }

    bitrix_client = Bitrix24Client()
    offset = 0

    async with async_session_maker() as db:
        while True:
            stmt = select(SurveySession).where(SurveySession.status == "completed")
            if only_missing:
                stmt = stmt.where(
                    (SurveySession.portal_clinic_bucket.is_(None))
                    | (SurveySession.bitrix_category_id.is_(None))
                )

            stmt = stmt.order_by(SurveySession.completed_at.asc().nullsfirst(), SurveySession.started_at.asc())
            if not only_missing:
                stmt = stmt.offset(offset)
            stmt = stmt.limit(batch_size)

            result = await db.execute(stmt)
            sessions = result.scalars().all()
            if not sessions:
                break

            for session in sessions:
                stats["processed"] += 1
                try:
                    deal_data = None
                    if session.lead_id:
                        deal_data = await bitrix_client.get_deal(session.lead_id)
                        if isinstance(deal_data, dict) and "ID" not in deal_data:
                            deal_data["ID"] = session.lead_id

                    category_id, clinic_bucket = bitrix_client.extract_portal_routing_from_deal(deal_data)
                    doctor_name = await bitrix_client.resolve_doctor_name_from_deal_data(deal_data)
                    if doctor_name is None:
                        doctor_name = bitrix_client.extract_doctor_name_from_deal(deal_data)

                    changed = False
                    if session.bitrix_category_id != category_id:
                        session.bitrix_category_id = category_id
                        changed = True
                    if session.portal_clinic_bucket != clinic_bucket:
                        session.portal_clinic_bucket = clinic_bucket
                        changed = True
                    if doctor_name and session.doctor_name != doctor_name:
                        session.doctor_name = doctor_name
                        changed = True

                    if clinic_bucket == Bitrix24Client.DEFAULT_PORTAL_CLINIC_BUCKET:
                        stats["routed_to_test"] += 1

                    if changed:
                        stats["updated"] += 1

                except Exception as exc:
                    stats["errors"] += 1
                    logger.exception(
                        "Не удалось обработать сессию doctor portal: "
                        f"session_id={session.id}, lead_id={session.lead_id}, error={exc}"
                    )

            await db.commit()
            logger.info(
                "Backfill doctor portal: "
                f"processed={stats['processed']}, updated={stats['updated']}, "
                f"test={stats['routed_to_test']}, errors={stats['errors']}"
            )
            if not only_missing:
                offset += batch_size

    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Заполняет вкладки doctor portal у завершенных сессий по данным Bitrix24.",
    )
    parser.add_argument("--batch-size", type=int, default=100, help="Размер пакета обработки")
    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="Обрабатывать только записи без заполненной вкладки или CATEGORY_ID",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    stats = await backfill_clinic_buckets(
        batch_size=max(1, args.batch_size),
        only_missing=args.only_missing,
    )
    logger.info(f"Backfill doctor portal завершен: {stats}")


if __name__ == "__main__":
    asyncio.run(main())
