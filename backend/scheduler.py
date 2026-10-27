import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from backend.config import load_settings
from backend.pipeline import execute_autonomous_pipeline, is_enrichment_running

logger = logging.getLogger("getmehired.scheduler")
scheduler = AsyncIOScheduler()

def run_scheduled_job():
    settings = load_settings()
    sched_cfg = settings.get("scheduler", {})
    if not sched_cfg.get("enabled", True):
        logger.info("Scheduler trigger skipped because scheduler is disabled in settings.")
        return

    # Overlap prevention: Skip new scrape if previous batch is still enriching
    if is_enrichment_running():
        logger.info("[Scheduler] Previous cycle is still actively analyzing jobs in background. Skipping new scrape to avoid queue buildup.")
        return

    interval = sched_cfg.get("interval_minutes", 45)
    logger.info(f"Executing {interval}-minute autonomous job hunter cycle...")
    try:
        execute_autonomous_pipeline()
    except Exception as e:
        logger.error(f"Scheduled pipeline run failed: {e}")

def init_scheduler():
    settings = load_settings()
    sched_cfg = settings.get("scheduler", {})
    interval = sched_cfg.get("interval_minutes", 45)

    # Add recurring interval job
    scheduler.add_job(
        run_scheduled_job,
        trigger=IntervalTrigger(minutes=interval),
        id="auto_job_hunter",
        name=f"GetMeHired {interval}-Minute Autonomous Pipeline",
        replace_existing=True
    )
    if not scheduler.running:
        scheduler.start()
        logger.info(f"GetMeHired Autonomous Scheduler started! Running every {interval} minutes.")

def restart_scheduler_with_interval(interval_minutes: int):
    try:
        scheduler.reschedule_job(
            job_id="auto_job_hunter",
            trigger=IntervalTrigger(minutes=interval_minutes)
        )
        logger.info(f"Scheduler rescheduled to run every {interval_minutes} minutes.")
    except Exception as e:
        logger.warning(f"Rescheduling notice: {e}")
