#!/usr/bin/env python3
"""DB-backed worker for Opros AI analysis and report delivery."""

import argparse
import asyncio

from loguru import logger

from app.core.database import async_session_maker
from app.services.ai_analysis.service import fetch_next_pending_ai_analysis, process_ai_analysis_job


async def process_once() -> bool:
    """Processes one pending job. Returns True when a job was handled."""
    async with async_session_maker() as db:
        analysis = await fetch_next_pending_ai_analysis(db)
        if not analysis:
            await db.commit()
            return False
        analysis_id = analysis.id
        logger.info(f"[AI-WORKER] Взята задача ИИ-анализа: analysis_id={analysis_id}")
        await process_ai_analysis_job(db, analysis)
        return True


async def run_worker(poll_interval_seconds: float = 5.0) -> None:
    logger.info("Запуск worker ИИ-анализа OpenRouter")
    while True:
        try:
            handled = await process_once()
            if not handled:
                await asyncio.sleep(poll_interval_seconds)
        except Exception as exc:
            logger.error(f"[AI-WORKER] Критическая ошибка worker-а: {exc}")
            await asyncio.sleep(poll_interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Обработать одну задачу и завершиться")
    parser.add_argument("--poll-interval", type=float, default=5.0, help="Интервал polling, секунды")
    args = parser.parse_args()

    if args.once:
        asyncio.run(process_once())
        return

    asyncio.run(run_worker(args.poll_interval))


if __name__ == "__main__":
    main()
