"""Notifications API for device registration and preferences."""
import json
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import get_db, User, DeviceToken, NotificationPreference
from app.api.auth import get_current_user
from app.services.push_notifications import DeadlineNotificationService

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


# ============ Schemas ============

class DeviceRegistration(BaseModel):
    device_token: str
    platform: str  # "ios" or "android"


class NotificationPreferencesRequest(BaseModel):
    deadline_reminders: bool = True
    application_updates: bool = True
    new_grant_alerts: bool = False
    reminder_days_before: List[int] = [7, 3, 1]


class NotificationPreferencesResponse(BaseModel):
    deadline_reminders: bool
    application_updates: bool
    new_grant_alerts: bool
    reminder_days_before: List[int]

    class Config:
        from_attributes = True


# ============ Endpoints ============

@router.post("/device")
async def register_device(
    request: DeviceRegistration,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register a device for push notifications."""
    # Check if token already exists for this user
    existing = db.query(DeviceToken).filter(
        DeviceToken.user_id == current_user.id,
        DeviceToken.device_token == request.device_token
    ).first()

    if existing:
        # Update last seen timestamp
        existing.updated_at = datetime.utcnow()
        db.commit()
        return {"message": "Device token updated"}

    # Create new device token
    device = DeviceToken(
        user_id=current_user.id,
        device_token=request.device_token,
        platform=request.platform
    )
    db.add(device)
    db.commit()

    return {"message": "Device registered successfully"}


@router.delete("/device")
async def unregister_device(
    request: DeviceRegistration,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unregister a device from push notifications."""
    device = db.query(DeviceToken).filter(
        DeviceToken.user_id == current_user.id,
        DeviceToken.device_token == request.device_token
    ).first()

    if device:
        db.delete(device)
        db.commit()

    return {"message": "Device unregistered"}


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get notification preferences for current user."""
    prefs = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id
    ).first()

    if not prefs:
        # Return defaults
        return NotificationPreferencesResponse(
            deadline_reminders=True,
            application_updates=True,
            new_grant_alerts=False,
            reminder_days_before=[7, 3, 1]
        )

    # Parse JSON for reminder_days_before
    days = [7, 3, 1]
    if prefs.reminder_days_before:
        try:
            days = json.loads(prefs.reminder_days_before)
        except json.JSONDecodeError:
            pass

    return NotificationPreferencesResponse(
        deadline_reminders=prefs.deadline_reminders,
        application_updates=prefs.application_updates,
        new_grant_alerts=prefs.new_grant_alerts,
        reminder_days_before=days
    )


@router.patch("/preferences", response_model=NotificationPreferencesResponse)
async def update_preferences(
    request: NotificationPreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update notification preferences for current user."""
    prefs = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id
    ).first()

    if not prefs:
        prefs = NotificationPreference(user_id=current_user.id)
        db.add(prefs)

    prefs.deadline_reminders = request.deadline_reminders
    prefs.application_updates = request.application_updates
    prefs.new_grant_alerts = request.new_grant_alerts
    prefs.reminder_days_before = json.dumps(request.reminder_days_before)
    prefs.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(prefs)

    return NotificationPreferencesResponse(
        deadline_reminders=prefs.deadline_reminders,
        application_updates=prefs.application_updates,
        new_grant_alerts=prefs.new_grant_alerts,
        reminder_days_before=request.reminder_days_before
    )


@router.post("/trigger-deadline-check")
async def trigger_deadline_check(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Manually trigger deadline reminder check (admin/testing)."""
    async def run_check():
        service = DeadlineNotificationService(db)
        await service.check_and_send_deadline_reminders()

    background_tasks.add_task(run_check)
    return {"message": "Deadline check triggered"}
