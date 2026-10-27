"""Create a self-contained example of monthly health-check monitoring.

The demo is safe to re-run: it only resets its own "Demo Lettuce" plant and
leaves every other plant untouched.

Usage:
    python manage.py seed_health_demo --username admin
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.farm.models import CareLog, DailyCheck, Plant, Reminder

DEMO_NAME = "Demo Lettuce (Health Check)"
HEALTH_MESSAGE = "Monthly health check: inspect the demo lettuce"


class Command(BaseCommand):
    help = "Create an example plant showing monthly health-check automation."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin")

    def handle(self, *args, **options):
        user = get_user_model().objects.filter(username=options["username"]).first()
        if not user:
            self.stderr.write(f'User "{options["username"]}" not found.')
            return

        today = date.today()
        plant = Plant.objects.filter(user=user, name=DEMO_NAME).first()
        if plant is None:
            plant = Plant(user=user, name=DEMO_NAME)

        # Reset only this demo plant's history so the example stays repeatable.
        if plant.pk:
            plant.reminders.all().delete()
            plant.daily_checks.all().delete()
            plant.care_logs.all().delete()

        plant.variety = "Romaine"
        plant.planting_date = today - timedelta(days=30)
        plant.days_to_harvest = 45
        plant.quantity = 6
        plant.status = "growing"
        plant.water_every_days = 1
        plant.fertilize_every_days = 14
        plant.health_check_every_days = 30
        plant.notes = (
            "Example plant created by `manage.py seed_health_demo`. "
            "Watch the monthly health-check reminder close and re-schedule."
        )
        area = user.garden_areas.order_by("id").first()
        if area:
            plant.area = area
            plant.pos_x = 0
            plant.pos_y = 0
        plant.save()

        # Health history: fair -> good -> excellent over the past month.
        DailyCheck.objects.create(
            user=user, plant=plant, date=today - timedelta(days=30),
            watered=True, health="fair", height_cm=8.0,
            notes="Older leaves slightly yellow; adjusted watering.",
        )
        DailyCheck.objects.create(
            user=user, plant=plant, date=today - timedelta(days=20),
            watered=True, fertilized=True, health="good", height_cm=9.5,
            notes="New growth and better color after the fix.",
        )
        DailyCheck.objects.create(
            user=user, plant=plant, date=today - timedelta(days=12),
            watered=True, health="excellent", height_cm=11.0,
            notes="Leaves firm, upright, and evenly green.",
        )
        CareLog.objects.create(
            user=user, plant=plant, date=today - timedelta(days=12),
            category="growth",
            description="Recovered from yellowing leaves; monthly check looks excellent.",
        )

        # One completed cycle + one monthly check due today.
        Reminder.objects.create(
            user=user, plant=plant, kind="health",
            message=HEALTH_MESSAGE, due_date=today - timedelta(days=30),
            is_done=True, done_at=today - timedelta(days=30),
        )
        Reminder.objects.create(
            user=user, plant=plant, kind="health",
            message=f"{HEALTH_MESSAGE} — due now (example)",
            due_date=today,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Example ready for "{user.username}".\n'
            f"  Plant:     {plant.name}\n"
            f"  History:   3 daily checks (fair -> good -> excellent)\n"
            f"  Due now:   1 monthly health check\n"
            f"  Next:      log a health status on the plant page, or click Done "
            f"on Reminders; the next check is scheduled 30 days later."
        ))
