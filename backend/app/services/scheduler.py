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

    scheduler.start()
    print("Background scheduler started")


def shutdown_scheduler():
    """Shutdown the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("Background scheduler stopped")
