"""Push notification service for sending notifications via APNs."""
import json
import time
import jwt
import httpx
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.database import DeviceToken, GrantProgram, User


class APNsService:
    """Service for sending push notifications via Apple Push Notification service."""

    # APNs endpoints
    SANDBOX_URL = "https://api.sandbox.push.apple.com"
    PRODUCTION_URL = "https://api.push.apple.com"

    def __init__(self):
        self.team_id = settings.apns_team_id
        self.key_id = settings.apns_key_id
        self.bundle_id = settings.apns_bundle_id
        self.key_path = settings.apns_key_path
        self.use_sandbox = settings.apns_use_sandbox
        self._token: Optional[str] = None
        self._token_expires: float = 0

    @property
    def base_url(self) -> str:
        return self.SANDBOX_URL if self.use_sandbox else self.PRODUCTION_URL

    def _generate_token(self) -> str:
        """Generate JWT token for APNs authentication."""
        if self._token and time.time() < self._token_expires:
            return self._token

        # Read private key
        try:
            with open(self.key_path, 'r') as f:
                private_key = f.read()
        except FileNotFoundError:
            raise ValueError(f"APNs key file not found: {self.key_path}")

        # Generate JWT
        headers = {
            "alg": "ES256",
            "kid": self.key_id
        }
        payload = {
            "iss": self.team_id,
            "iat": int(time.time())
        }

        self._token = jwt.encode(payload, private_key, algorithm="ES256", headers=headers)
        self._token_expires = time.time() + 3500  # Token valid for ~1 hour

        return self._token

    async def send_notification(
        self,
        device_token: str,
        title: str,
        body: str,
        data: Optional[dict] = None,
        badge: Optional[int] = None,
        sound: str = "default"
    ) -> bool:
        """Send a push notification to a single device."""
        if not all([self.team_id, self.key_id, self.bundle_id, self.key_path]):
            print("APNs not configured, skipping push notification")
            return False

        try:
            token = self._generate_token()
        except ValueError as e:
            print(f"Failed to generate APNs token: {e}")
            return False

        # Build payload
        aps = {
            "alert": {
                "title": title,
                "body": body
            },
            "sound": sound
        }
        if badge is not None:
            aps["badge"] = badge

        payload = {"aps": aps}
        if data:
            payload.update(data)

        # Send request
        url = f"{self.base_url}/3/device/{device_token}"
        headers = {
            "authorization": f"bearer {token}",
            "apns-topic": self.bundle_id,
            "apns-push-type": "alert",
            "apns-priority": "10"
        }

        async with httpx.AsyncClient(http2=True) as client:
            try:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )

                if response.status_code == 200:
                    return True
                else:
                    print(f"APNs error: {response.status_code} - {response.text}")
                    return False

            except Exception as e:
                print(f"Failed to send push notification: {e}")
                return False

    async def send_to_user(
        self,
        db: Session,
        user_id: str,
        title: str,
        body: str,
        data: Optional[dict] = None
    ) -> int:
        """Send a push notification to all devices for a user."""
        devices = db.query(DeviceToken).filter(
            DeviceToken.user_id == user_id,
            DeviceToken.platform == "ios"
        ).all()

        sent = 0
        for device in devices:
            if await self.send_notification(device.device_token, title, body, data):
                sent += 1

        return sent


class DeadlineNotificationService:
    """Service for managing deadline reminder notifications."""

    def __init__(self, db: Session):
        self.db = db
        self.apns = APNsService()

    async def check_and_send_deadline_reminders(self):
        """Check for upcoming deadlines and send reminders."""
        # Get programs with deadlines in the next 7 days
        now = datetime.utcnow()
        reminder_windows = [
            (7, "in 7 days"),
            (3, "in 3 days"),
            (1, "tomorrow")
        ]

        for days, time_text in reminder_windows:
            target_date = now + timedelta(days=days)
            start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

            programs = self.db.query(GrantProgram).filter(
                GrantProgram.deadline >= start_of_day,
                GrantProgram.deadline <= end_of_day,
                GrantProgram.is_active.is_(True)
            ).all()

            for program in programs:
                await self._send_deadline_reminder(program, time_text)

    async def _send_deadline_reminder(self, program: GrantProgram, time_text: str):
        """Send deadline reminder for a specific program to interested users."""
        # Get all users with deadline_reminders enabled
        from app.models.database import NotificationPreference

        prefs = self.db.query(NotificationPreference).filter(
            NotificationPreference.deadline_reminders.is_(True)
        ).all()

        user_ids = [p.user_id for p in prefs]

        # Also include users without preferences (default is enabled)
        all_user_ids = self.db.query(User.id).all()
        users_with_prefs = set(user_ids)
        default_users = [u.id for u in all_user_ids if u.id not in users_with_prefs]
        user_ids.extend(default_users)

        for user_id in user_ids:
            await self.apns.send_to_user(
                self.db,
                user_id,
                title="Grant Deadline Approaching",
                body=f"{program.name} deadline is {time_text}. Don't miss out!",
                data={
                    "type": "deadline_reminder",
                    "grantId": program.id
                }
            )

    async def send_application_update(
        self,
        user_id: str,
        application_id: str,
        program_name: str,
        status: str
    ):
        """Send notification about application status update."""
        await self.apns.send_to_user(
            self.db,
            user_id,
            title="Application Update",
            body=f"Your {program_name} application is now {status}.",
            data={
                "type": "application_update",
                "applicationId": application_id
            }
        )


# Singleton instance
apns_service = APNsService()
