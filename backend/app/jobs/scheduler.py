"""Background job scheduler using APScheduler."""
from __future__ import annotations

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.jobs.overdue_scan import run_overdue_scan

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _overdue_scan_task() -> None:
    """Wrapper to run overdue scan inside a scoped DB session."""
    db = SessionLocal()
    try:
        run_overdue_scan(db)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Error running scheduled overdue scan: %s", exc, exc_info=True)
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler | None:
    """Start background scheduler if ENABLE_SCHEDULER is True."""
    global _scheduler
    settings = get_settings()

    if not settings.enable_scheduler:
        logger.info("Scheduler is disabled via ENABLE_SCHEDULER=false")
        return None

    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _overdue_scan_task,
        trigger=IntervalTrigger(minutes=settings.overdue_scan_interval_minutes),
        id="overdue_scan",
        name="Scan for overdue complaints",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "Scheduler started. Overdue scan interval: %d minutes",
        settings.overdue_scan_interval_minutes,
    )
    return _scheduler


def shutdown_scheduler() -> None:
    """Stop the background scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")
