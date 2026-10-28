"""Create self-contained examples of monthly health-check monitoring.

Seeds two demo plants:

* **Demo Lettuce (Good Health)** — monthly history trending fair -> good ->
  excellent, with a monthly health check due today.
* **Demo Tomato (Poor Health)** — monthly history trending good -> fair ->
  poor, with a monthly health check and a follow-up alert due today.

The demo is safe to re-run: it resets only its own demo plants and leaves
every other plant untouched.

Usage:
    python manage.py seed_health_demo --username admin
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.farm.models import CareLog, DailyCheck, Plant, Reminder

GOOD_NAME = "Demo Lettuce (Good Health)"
BAD_NAME = "Demo Tomato (Poor Health)"
LEGACY_NAME = "Demo Lettuce (Health Check)"


class Command(BaseCommand):
    help = "Create good and poor examples of monthly health-check monitoring."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin")

    def _reset_plant(self, user, name):
        """Return this demo plant, wiping only its own history for re-runs."""
        plant = Plant.objects.filter(user=user, name=name).first()
        if plant is None:
            return Plant(user=user, name=name)
        plant.reminders.all().delete()
        plant.daily_checks.all().delete()
        plant.care_logs.all().delete()
        return plant

    def handle(self, *args, **options):
        user = get_user_model().objects.filter(username=options["username"]).first()
        if not user:
            self.stderr.write(f'User "{options["username"]}" not found.')
            return

        today = date.today()
        area = user.garden_areas.order_by("id").first()

        # Remove the plant created by the earlier single-example version.
        Plant.objects.filter(user=user, name=LEGACY_NAME).delete()

        # ---------- good example ----------
        good = self._reset_plant(user, GOOD_NAME)
        good.variety = "Romaine"
        good.planting_date = today - timedelta(days=30)
        good.start_method = "transplant"
        good.days_to_harvest = 45
        good.quantity = 6
        good.status = "growing"
        good.water_every_days = 1
        good.fertilize_every_days = 14
        good.health_check_every_days = 30
        good.notes = (
            "Demo created by `manage.py seed_health_demo`. Monthly health is "
            "trending up; latest status is Excellent."
        )
        if area:
            good.area = area
            good.pos_x = 0
            good.pos_y = 0
        good.save()

        DailyCheck.objects.create(
            user=user, plant=good, date=today - timedelta(days=30),
            watered=True, health="fair", height_cm=8.0,
            notes="Baseline monthly check: older leaves slightly pale.",
        )
        DailyCheck.objects.create(
            user=user, plant=good, date=today - timedelta(days=20),
            watered=True, fertilized=True, health="good", height_cm=9.5,
            notes="New growth and better color after adjusting watering.",
        )
        DailyCheck.objects.create(
            user=user, plant=good, date=today - timedelta(days=12),
            watered=True, health="good", height_cm=11.0,
            notes="Leaves firm, upright, and evenly green.",
        )
        DailyCheck.objects.create(
            user=user, plant=good, date=today - timedelta(days=2),
            watered=True, health="excellent", height_cm=12.0,
            notes="Monthly check: vigorous growth, no pests or disease.",
        )
        CareLog.objects.create(
            user=user, plant=good, date=today - timedelta(days=2),
            category="growth",
            description="Monthly health check: excellent. No pest or disease signs.",
        )
        Reminder.objects.create(
            user=user, plant=good, kind="health",
            message=f"Monthly health check: inspect the {good.name.lower()}",
            due_date=today - timedelta(days=30),
            is_done=True, done_at=today - timedelta(days=30),
        )
        Reminder.objects.create(
            user=user, plant=good, kind="health",
            message=f"Monthly health check: inspect the {good.name.lower()} — due now (good example)",
            due_date=today,
        )

        # ---------- poor example ----------
        bad = self._reset_plant(user, BAD_NAME)
        bad.variety = "Cherry"
        bad.planting_date = today - timedelta(days=45)
        bad.start_method = "transplant"
        bad.days_to_harvest = 75
        bad.quantity = 4
        bad.status = "growing"
        bad.water_every_days = 2
        bad.fertilize_every_days = 14
        bad.health_check_every_days = 30
        bad.notes = (
            "Demo created by `manage.py seed_health_demo`. Monthly health is "
            "declining; latest status is Poor and needs attention."
        )
        if area:
            bad.area = area
            bad.pos_x = 1
            bad.pos_y = 0
        bad.save()

        DailyCheck.objects.create(
            user=user, plant=bad, date=today - timedelta(days=35),
            watered=True, health="good", height_cm=25.0,
            notes="Baseline monthly check: healthy, even color.",
        )
        DailyCheck.objects.create(
            user=user, plant=bad, date=today - timedelta(days=25),
            watered=True, fertilized=True, health="fair", height_cm=27.0,
            notes="Some lower leaves yellowing; reduced watering.",
        )
        DailyCheck.objects.create(
            user=user, plant=bad, date=today - timedelta(days=12),
            watered=True, health="fair", height_cm=28.0,
            notes="Spots spreading on lower leaves; watching closely.",
        )
        DailyCheck.objects.create(
            user=user, plant=bad, date=today - timedelta(days=1),
            watered=True, health="poor", height_cm=28.5,
            notes="Wilting and yellow lower leaves; possible blight. Needs attention.",
        )
        CareLog.objects.create(
            user=user, plant=bad, date=today - timedelta(days=5),
            category="pest",
            description="Aphids and possible blight on lower leaves; removed affected leaves and applied neem oil.",
        )
        CareLog.objects.create(
            user=user, plant=bad, date=today - timedelta(days=1),
            category="note",
            description="Monthly health check: poor. Monitoring daily for recovery.",
        )
        Reminder.objects.create(
            user=user, plant=bad, kind="health",
            message=f"Monthly health check: inspect the {bad.name.lower()}",
            due_date=today - timedelta(days=30),
            is_done=True, done_at=today - timedelta(days=30),
        )
        Reminder.objects.create(
            user=user, plant=bad, kind="health",
            message=f"Monthly health check: inspect the {bad.name.lower()} — due now (poor example)",
            due_date=today,
        )
        Reminder.objects.create(
            user=user, plant=bad, kind="custom",
            message=f"Check the struggling {bad.name.lower()} — poor health reported",
            due_date=today,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Monthly-health demos ready for "{user.username}".\n'
            f"  Good:  {good.name}\n"
            f"         history fair -> good -> good -> excellent\n"
            f"         1 monthly health check due today\n"
            f"  Bad:   {bad.name}\n"
            f"         history good -> fair -> fair -> poor\n"
            f"         1 monthly health check + 1 follow-up alert due today\n"
            f"  Open Plants to see the latest health badges, or Reminders to "
            f"complete the checks and roll the next one 30 days later."
        ))
