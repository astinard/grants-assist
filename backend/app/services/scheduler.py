"""Background job scheduler for GrantsAssist."""
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.models.database import SessionLocal
from app.services.push_notifications import DeadlineNotificationService


scheduler = AsyncIOScheduler()


async def check_deadline_reminders():
    """Job to check and send deadline reminders."""
    print(f"[{datetime.utcnow()}] Running deadline reminder check...")

    db = SessionLocal()
    try:
        service = DeadlineNotificationService(db)
        await service.check_and_send_deadline_reminders()
        print(f"[{datetime.utcnow()}] Deadline reminder check completed")
    except Exception as e:
        print(f"[{datetime.utcnow()}] Error in deadline reminder check: {e}")
    finally:
        db.close()


def sync_grants_gov_job():
    """Job to sync grants from Grants.gov daily."""
    print(f"[{datetime.utcnow()}] Running Grants.gov sync...")

    db = SessionLocal()
    try:
        from app.services.grants_gov_fetcher import sync_grants_gov, create_grants_gov_fetcher

        # Sync all open grants
        stats = sync_grants_gov(db)
        print(f"[{datetime.utcnow()}] Grants.gov sync completed: {stats['imported']} imported, {stats['updated']} updated")

        # Mark expired grants as inactive
        fetcher = create_grants_gov_fetcher(db)
        expired = fetcher.mark_expired_inactive()
        print(f"[{datetime.utcnow()}] Marked {expired} expired grants as inactive")

    except Exception as e:
        print(f"[{datetime.utcnow()}] Error in Grants.gov sync: {e}")
    finally:
        db.close()


def sync_state_grants_job():
    """Job to sync grants from state portals daily."""
    print(f"[{datetime.utcnow()}] Running state grants sync...")

    db = SessionLocal()
    try:
        from app.services.state_grants_fetcher import sync_california_grants, create_california_fetcher

        # Sync California grants
        ca_stats = sync_california_grants(db)
        print(f"[{datetime.utcnow()}] California sync: {ca_stats['imported']} imported, {ca_stats['updated']} updated")

        # Mark expired California grants as inactive
        fetcher = create_california_fetcher(db)
        ca_expired = fetcher.mark_expired_inactive()
        print(f"[{datetime.utcnow()}] Marked {ca_expired} expired CA grants as inactive")

    except Exception as e:
        print(f"[{datetime.utcnow()}] Error in state grants sync: {e}")
    finally:
        db.close()


def start_scheduler():
    """Initialize and start the background scheduler."""
    # Check for deadline reminders every day at 9 AM UTC
    scheduler.add_job(
        check_deadline_reminders,
        CronTrigger(hour=9, minute=0),
        id="deadline_reminders",
        name="Check and send deadline reminders",
        replace_existing=True
    )

    # Sync grants from Grants.gov every day at 5 AM UTC
    # This runs before deadline reminders to ensure fresh data
    scheduler.add_job(
        sync_grants_gov_job,
        CronTrigger(hour=5, minute=0),
        id="grants_gov_sync",
        name="Sync grants from Grants.gov",
        replace_existing=True
    )

    # Sync grants from state portals every day at 6 AM UTC
    # Runs after Grants.gov sync, before deadline reminders
    scheduler.add_job(
        sync_state_grants_job,
        CronTrigger(hour=6, minute=0),
        id="state_grants_sync",
        name="Sync grants from state portals",
        replace_existing=True
    )

    scheduler.start()
    print("Background scheduler started")


def shutdown_scheduler():
    """Shutdown the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("Background scheduler stopped")
