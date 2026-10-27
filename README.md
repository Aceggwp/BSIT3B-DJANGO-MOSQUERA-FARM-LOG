# MOSQUERA Farm Logs

Django farm management app: planting & harvest tracking, custom reminders
(weather-adaptive via Open-Meteo), visual garden layout map with companion
planting alerts, care history with progress photos, daily monitoring with
quick-log shortcuts, automated monthly health checks, AI advice
(Gemini / OpenRouter), role-based auth (admin + staff), and login tracking.

## Members

- Mosquera, Carl John
- Lirazan, Adrian
- Lucasan, Arc Xerlan 

## Initial table design

See [`docs/initial-table-design.md`](docs/initial-table-design.md)
for the ERD, table/column specs, and constraints, or
[`SQL/farm_schema.sql`](SQL/farm_schema.sql) for a clean
MariaDB/MySQL DDL of the farm tables.

## Run locally

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Automation

Completing a water/fertilize reminder auto-schedules the next occurrence,
and logging a health status in **Daily Monitoring** completes the due
monthly health check and schedules the next one. Plant edits sync open
reminders. To backfill/ensure reminders on a schedule, run
`python manage.py sync_reminders` (idempotent) via cron or Windows Task
Scheduler.

### Monthly health checks

Every plant has a recurring **Health check** reminder driven by
`health_check_every_days` (default **30 days**):

- New plants get a health-check reminder automatically.
- Completing it — or saving any health status in **Daily Monitoring** — marks
  the current check done and creates the next one from that date.
- The plant page shows the **latest health** (Poor / Fair / Good / Excellent)
  and the **next check date**.
- Health checks appear on the **Dashboard → Due now** and the **Reminders**
  page with a 🩺 badge, alongside water, fertilize, and harvest tasks.
- Change the cadence per plant under **Plants → Add/Edit Plant → Health check
  every (days)**.
- Existing plants are backfilled by `python manage.py sync_reminders`.

### Load the example

The demo command is safe to re-run: it resets only its own demo plant.

```bash
python manage.py seed_health_demo --username admin
```

It creates **Demo Lettuce (Health Check)** with three daily checks
(Fair → Good → Excellent), one completed monthly check, and one check due
today. Open the plant, save a health status (or click **Done** on the
reminder), and the next check is scheduled 30 days later.

## Optional integrations

Set via environment variables (no keys needed for the default weather
provider):

```bash
set FARM_WEATHER_LAT=14.5995
set FARM_WEATHER_LON=120.9842
set GEMINI_API_KEY=your_key
set AI_PROVIDER=gemini
set OPENROUTER_API_KEY=your_key   # with AI_PROVIDER=openrouter
```
