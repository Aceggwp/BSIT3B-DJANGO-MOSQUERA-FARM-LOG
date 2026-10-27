"""Keep plants and reminders in sync (idempotent — safe to schedule).

Ensures every plant has open water/fertilize/harvest reminders, re-syncs
auto harvest dates/messages to each plant's current schedule, and reports.

Usage:
    python manage.py sync_reminders

Schedule it (Windows Task Scheduler or cron) for hands-free automation,
e.g. daily. Per-action automation (rollover on Done, edit sync) already
runs inside the app; this command backfills anything missed.
"""

import re

from django.core.management.base import BaseCommand

from apps.farm.models import Plant, Reminder

AUTO_HARVEST = re.compile(r"^Harvest the .+ around (\d{4}-\d{2}-\d{2})$")


class Command(BaseCommand):
    help = "Ensure + re-sync plant reminders (idempotent)."

    def handle(self, *args, **options):
        ensured = resynced = 0
        plants = Plant.objects.order_by("id")
        self.stdout.write(f"Checking {plants.count()} plant(s)...")
        for plant in plants:
            pending = set(plant.reminders.filter(is_done=False).values_list("kind", flat=True))
            fresh = [r for r in Reminder.build_defaults_for_plant(plant) if r.kind not in pending]
            if fresh:
                Reminder.objects.bulk_create(fresh)
                ensured += len(fresh)
                self.stdout.write(f"  {plant.name}: +{len(fresh)} reminder(s) ensured")
            expected = plant.expected_harvest_date
            for r in plant.reminders.filter(is_done=False, kind="harvest"):
                m = AUTO_HARVEST.match(r.message)
                if m and (m.group(1) != str(expected) or r.due_date != expected):
                    r.message = f"Harvest the {plant.name.lower()} around {expected}"
                    r.due_date = expected
                    r.save(update_fields=["message", "due_date"])
                    resynced += 1
                    self.stdout.write(f"  {plant.name}: harvest re-synced to {expected}")
        self.stdout.write(self.style.SUCCESS(
            f"sync complete: {ensured} ensured, {resynced} harvest re-synced."))
