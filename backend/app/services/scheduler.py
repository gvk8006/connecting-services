"""
Scheduler Service - Runs the agent pipeline on a recurring schedule.
Uses APScheduler to periodically run: Prospector -> Qualifier -> Outreach Connector
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _run_pipeline():
    """Run the full agent pipeline: prospect -> qualify -> outreach."""
    from app.services.orchestrator import orchestrator

    logger.info("Scheduler: Starting automated pipeline run...")
    try:
        result = await orchestrator.run_all_agents()
        logger.info(f"Scheduler: Pipeline completed: {result}")
    except Exception as e:
        logger.error(f"Scheduler: Pipeline failed: {e}")


def start_scheduler(prospect_interval_hours: int = 4):
    """Start the background scheduler.

    Args:
        prospect_interval_hours: How often to run the full pipeline (default: 4 hours).
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("Scheduler already running")
        return

    _scheduler = AsyncIOScheduler()

    _scheduler.add_job(
        _run_pipeline,
        trigger=IntervalTrigger(hours=prospect_interval_hours),
        id="pipeline_run",
        name="Full Agent Pipeline",
        replace_existing=True,
        max_instances=1,
    )

    _scheduler.start()
    logger.info(
        f"Scheduler started. Pipeline will run every {prospect_interval_hours} hours."
    )


def stop_scheduler():
    """Gracefully stop the scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped.")
