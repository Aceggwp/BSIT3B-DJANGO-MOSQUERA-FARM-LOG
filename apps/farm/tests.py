from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.farm.models import CareLog, DailyCheck, GardenArea, Plant, Reminder, defaults_for


class FarmModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="farmer", password="secret1234")

    def test_harvest_date_calculation(self):
        plant = Plant.objects.create(
            user=self.user, name="Lettuce",
            planting_date=date.today() - timedelta(days=10),
            days_to_harvest=45,
        )
        self.assertEqual(plant.expected_harvest_date, date.today() + timedelta(days=35))
        self.assertEqual(plant.days_until_harvest, 35)

    def test_vegetable_defaults_tailored(self):
        self.assertEqual(defaults_for("lettuce")["water_every_days"], 1)
        self.assertEqual(defaults_for("tomato")["days_to_harvest"], 75)
        self.assertEqual(defaults_for("tomato", "direct")["days_to_harvest"], 100)
        self.assertEqual(defaults_for("tomato", "transplant")["days_to_harvest"], 75)
        self.assertEqual(defaults_for("Carrots")["days_to_harvest"], 70)
        self.assertEqual(defaults_for("Peppers")["days_to_harvest"], 75)
        self.assertEqual(defaults_for("Cucumbers")["days_to_harvest"], 55)
        self.assertEqual(defaults_for("Tomatoes")["days_to_harvest"], 75)
        self.assertEqual(defaults_for("Pechay")["days_to_harvest"], 35)
        self.assertTrue(defaults_for("Rambutan")["known"])
        self.assertEqual(defaults_for("Rambutan")["days_to_harvest"], 1095)

    def test_apply_defaults_sets_start_method(self):
        plant = Plant(user=self.user, name="Tomato")
        plant.apply_vegetable_defaults()
        self.assertEqual(plant.days_to_harvest, 75)
        self.assertEqual(plant.start_method, "transplant")

        direct = Plant(user=self.user, name="Tomato", start_method="direct")
        direct.apply_vegetable_defaults()
        self.assertEqual(direct.days_to_harvest, 100)
        self.assertEqual(direct.start_method, "direct")

        tree = Plant(user=self.user, name="Rambutan")
        tree.apply_vegetable_defaults()
        self.assertEqual(tree.days_to_harvest, 1095)
        self.assertEqual(tree.start_method, "transplant")

        seed_tree = Plant(user=self.user, name="Rambutan", start_method="direct")
        seed_tree.apply_vegetable_defaults()
        self.assertEqual(seed_tree.days_to_harvest, 2190)
        self.assertEqual(seed_tree.start_method, "direct")

    def test_reminder_status_badges(self):
        plant = Plant.objects.create(user=self.user, name="Lettuce", planting_date=date.today())
        late = Reminder.objects.create(user=self.user, plant=plant, kind="water",
                                       message="late", due_date=date.today() - timedelta(days=3))
        today_r = Reminder.objects.create(user=self.user, plant=plant, kind="custom",
                                          message="now", due_date=date.today())
        self.assertEqual(late.days_overdue, 3)
        self.assertTrue(today_r.is_due_today)
        self.client.force_login(self.user)
        response = self.client.get(reverse("farm:reminder_list"))
        self.assertContains(response, "3d overdue")
        self.assertContains(response, "Due today")
        self.assertContains(response, "badge-pulse")

    def test_reminder_defaults_generation(self):
        plant = Plant.objects.create(user=self.user, name="Tomato", planting_date=date.today())
        plant.apply_vegetable_defaults()
        plant.save()
        rems = Reminder.build_defaults_for_plant(plant)
        kinds = {r.kind for r in rems}
        self.assertEqual(kinds, {"water", "fertilize", "harvest"})
        Reminder.objects.bulk_create(rems)
        self.assertEqual(plant.reminders.count(), 3)
        self.assertIn("tomato", plant.reminders.first().message.lower())

    def test_daily_check_unique_per_day(self):
        plant = Plant.objects.create(user=self.user, name="Okra")
        DailyCheck.objects.create(user=self.user, plant=plant, date=date.today())
        with self.assertRaises(Exception):
            DailyCheck.objects.create(user=self.user, plant=plant, date=date.today())

    def test_scoping_other_user_cannot_access(self):
        other = get_user_model().objects.create_user(username="other", password="x" * 10)
        plant = Plant.objects.create(user=self.user, name="Beans")
        self.client.force_login(other)
        response = self.client.get(reverse("farm:plant_detail", args=[plant.id]))
        self.assertEqual(response.status_code, 404)


class FarmCropCatalogTests(TestCase):
    def test_rambutan_lookup_and_ranges(self):
        from apps.farm.crops import resolve_crop

        key, profile, known = resolve_crop("Rambutan")
        self.assertTrue(known)
        self.assertEqual(key, "rambutan")
        self.assertEqual(profile["days"], {"direct": 2190, "transplant": 1095})
        self.assertEqual(
            profile["ranges"],
            {"direct": (1825, 2555), "transplant": (730, 1460)},
        )

        default = defaults_for("Rambutan")
        self.assertEqual(default["days_to_harvest"], 1095)
        self.assertEqual(default["days_min"], 730)
        self.assertEqual(default["days_max"], 1460)
        self.assertEqual(default["start_method"], "transplant")

    def test_tree_crop_local_aliases(self):
        aliases = {
            "rambotan": "rambutan",
            "mangga": "mango",
            "carabao mango": "mango",
            "kalamansi": "calamansi",
            "limonsito": "calamansi",
            "kapayas": "papaya",
            "saging": "banana",
            "lakatan": "banana",
            "langka": "jackfruit",
            "abokado": "avocado",
            "lansones": "lanzones",
            "duryan": "durian",
        }
        for alias, expected in aliases.items():
            with self.subTest(alias=alias):
                guide = defaults_for(alias)
                self.assertTrue(guide["known"])
                self.assertEqual(guide["crop_key"], expected)

    def test_tree_crop_start_method_overrides(self):
        cases = [
            ("Rambutan", "direct", 2190),
            ("Rambutan", "transplant", 1095),
            ("Mango", "direct", 2555),
            ("Mango", "transplant", 1095),
            ("Calamansi", "direct", 1460),
            ("Calamansi", "transplant", 548),
            ("Papaya", "direct", 300),
            ("Papaya", "transplant", 240),
            ("Banana", "direct", 450),
            ("Banana", "transplant", 300),
            ("Jackfruit", "direct", 2555),
            ("Jackfruit", "transplant", 1460),
            ("Avocado", "direct", 2555),
            ("Avocado", "transplant", 1460),
            ("Lanzones", "direct", 2920),
            ("Lanzones", "transplant", 1825),
            ("Durian", "direct", 3285),
            ("Durian", "transplant", 1825),
        ]
        for name, method, expected_days in cases:
            with self.subTest(name=name, method=method):
                guide = defaults_for(name, method)
                self.assertEqual(guide["days_to_harvest"], expected_days)
                self.assertEqual(guide["start_method"], method)

    def test_crop_guide_payload_includes_tree_crops_and_aliases(self):
        from apps.farm.crops import crop_guide_payload

        payload = crop_guide_payload()
        self.assertIn("rambutan", payload["crops"])
        self.assertEqual(payload["aliases"]["mangga"], "mango")
        self.assertEqual(payload["aliases"]["kalamansi"], "calamansi")
        self.assertEqual(
            payload["crops"]["rambutan"]["days"],
            {"direct": 2190, "transplant": 1095},
        )
        self.assertEqual(
            payload["crops"]["rambutan"]["ranges"]["transplant"],
            [730, 1460],
        )

    def test_duration_filters_render_years_for_large_values(self):
        from apps.farm.templatetags.farm_filters import days_duration, days_range

        self.assertEqual(days_duration(45), "45 days")
        self.assertEqual(days_duration(1095), "1,095 days (~3.0 years)")
        self.assertEqual(
            days_range(1825, 2555),
            "1,825 days (~5.0 years) – 2,555 days (~7.0 years)",
        )
        self.assertEqual(days_range(30, 55), "30–55 days")


class FarmViewTests(TestCase):
    def setUp(self):
        import tempfile
        from django.test import override_settings
        self._media = tempfile.mkdtemp()
        self._media_override = override_settings(MEDIA_ROOT=self._media)
        self._media_override.enable()
        self.addCleanup(self._media_override.disable)
        self.user = get_user_model().objects.create_user(username="farmer2", password="secret1234")
        self.client.force_login(self.user)

    def test_dashboard_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("farm:dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_create_plant_generates_reminders(self):
        response = self.client.post(reverse("farm:plant_save_ajax"), {
            "name": "Lettuce", "planting_date": date.today().isoformat(),
        })
        self.assertEqual(response.status_code, 200)
        plant = Plant.objects.get(user=self.user, name="Lettuce")
        self.assertEqual(plant.reminders.count(), 3)
        self.assertEqual(plant.start_method, "direct")
        self.assertEqual(plant.days_to_harvest, 45)

    def test_create_plant_uses_start_method_for_harvest_days(self):
        response = self.client.post(reverse("farm:plant_save_ajax"), {
            "name": "Tomato", "start_method": "transplant",
            "planting_date": date.today().isoformat(),
        })
        self.assertEqual(response.status_code, 200)
        transplanted = Plant.objects.get(user=self.user, name="Tomato")
        self.assertEqual(transplanted.start_method, "transplant")
        self.assertEqual(transplanted.days_to_harvest, 75)
        self.assertEqual(
            transplanted.expected_harvest_date,
            date.today() + timedelta(days=75),
        )

        response = self.client.post(reverse("farm:plant_save_ajax"), {
            "name": "Tomato", "start_method": "direct",
            "planting_date": date.today().isoformat(),
        })
        self.assertEqual(response.status_code, 200)
        direct = Plant.objects.filter(user=self.user, name="Tomato").order_by("-id").first()
        self.assertEqual(direct.start_method, "direct")
        self.assertEqual(direct.days_to_harvest, 100)

    def test_create_tree_crop_uses_catalog_transplant_defaults(self):
        response = self.client.post(reverse("farm:plant_save_ajax"), {
            "name": "Rambutan", "planting_date": date.today().isoformat(),
        })
        self.assertEqual(response.status_code, 200)
        plant = Plant.objects.get(user=self.user, name="Rambutan")
        self.assertEqual(plant.start_method, "transplant")
        self.assertEqual(plant.days_to_harvest, 1095)
        self.assertEqual(plant.water_every_days, 3)
        self.assertEqual(plant.fertilize_every_days, 30)
        self.assertEqual(
            plant.expected_harvest_date,
            date.today() + timedelta(days=1095),
        )

    def test_tree_crop_detail_shows_year_estimates(self):
        plant = Plant.objects.create(
            user=self.user, name="Rambutan",
            planting_date=date.today(),
            start_method="transplant", days_to_harvest=1095,
        )
        response = self.client.get(reverse("farm:plant_detail", args=[plant.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1,095 days (~3.0 years)")
        self.assertContains(
            response,
            "730 days (~2.0 years) – 1,460 days (~4.0 years)",
        )

    def test_create_plant_keeps_explicit_harvest_override(self):
        response = self.client.post(reverse("farm:plant_save_ajax"), {
            "name": "Tomato", "start_method": "transplant",
            "planting_date": date.today().isoformat(),
            "days_to_harvest": "60", "water_every_days": "3",
            "fertilize_every_days": "10",
        })
        self.assertEqual(response.status_code, 200)
        plant = Plant.objects.get(user=self.user, name="Tomato")
        self.assertEqual(plant.days_to_harvest, 60)
        self.assertEqual(plant.water_every_days, 3)
        self.assertEqual(plant.fertilize_every_days, 10)
        self.assertEqual(plant.start_method, "transplant")

    def test_daily_check_marks_reminder_done(self):
        plant = Plant.objects.create(user=self.user, name="Lettuce", planting_date=date.today())
        rem = Reminder.objects.create(
            user=self.user, plant=plant, kind="water",
            message="Water the lettuce today", due_date=date.today(),
        )
        self.client.post(reverse("farm:dailycheck_save_ajax", args=[plant.id]), {
            "date": date.today().isoformat(), "watered": "true", "health": "good",
        })
        rem.refresh_from_db()
        self.assertTrue(rem.is_done)

    def test_care_log_create(self):
        plant = Plant.objects.create(user=self.user, name="Pepper")
        response = self.client.post(reverse("farm:carelog_save_ajax", args=[plant.id]), {
            "category": "pest", "description": "Aphids spotted",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CareLog.objects.filter(plant=plant).exists())

    def test_care_log_photo_upload(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        plant = Plant.objects.create(user=self.user, name="Pepper")
        gif = (b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!'
               b'\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')
        photo = SimpleUploadedFile("growth.gif", gif, content_type="image/gif")
        response = self.client.post(reverse("farm:carelog_save_ajax", args=[plant.id]), {
            "category": "growth", "description": "First leaves", "photo": photo,
        })
        self.assertEqual(response.status_code, 200)
        log = CareLog.objects.get(plant=plant)
        self.assertTrue(log.photo.name.startswith("care_photos/"))
        self.assertTrue(response.json()["photo_url"].endswith(".gif"))

    def test_care_log_rejects_non_image(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        plant = Plant.objects.create(user=self.user, name="Pepper")
        bad = SimpleUploadedFile("note.txt", b"hello", content_type="text/plain")
        response = self.client.post(reverse("farm:carelog_save_ajax", args=[plant.id]), {
            "category": "note", "description": "x", "photo": bad,
        })
        self.assertEqual(response.status_code, 400)

    def test_carelog_list_page(self):
        p1 = Plant.objects.create(user=self.user, name="Pepper", planting_date=date.today())
        p2 = Plant.objects.create(user=self.user, name="Lettuce", planting_date=date.today())
        CareLog.objects.create(user=self.user, plant=p1, date=date.today(),
                               category="pest", description="Aphids")
        CareLog.objects.create(user=self.user, plant=p2, date=date.today(),
                               category="growth", description="Sprouted")
        response = self.client.get(reverse("farm:carelog_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aphids")
        self.assertContains(response, "Sprouted")
        filtered = self.client.get(reverse("farm:carelog_list"), {"plant": p1.id})
        self.assertContains(filtered, "Aphids")
        self.assertNotContains(filtered, "Sprouted")
        by_cat = self.client.get(reverse("farm:carelog_list"), {"category": "pest"})
        self.assertContains(by_cat, "Aphids")
        self.assertNotContains(by_cat, "Sprouted")

    def test_carelog_list_scoped(self):
        other = get_user_model().objects.create_user(username="log_other", password="secret1234")
        plant = Plant.objects.create(user=other, name="Secret", planting_date=date.today())
        CareLog.objects.create(user=other, plant=plant, date=date.today(),
                               category="note", description="Hidden gem")
        response = self.client.get(reverse("farm:carelog_list"))
        self.assertNotContains(response, "Hidden gem")


class FarmQuickLogTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="quick", password="secret1234")
        self.area = GardenArea.objects.create(user=self.user, name="Bed 1", rows=2, cols=2)
        self.p1 = Plant.objects.create(user=self.user, name="Lettuce", area=self.area,
                                       planting_date=date.today())
        self.p2 = Plant.objects.create(user=self.user, name="Tomato",
                                       planting_date=date.today())
        self.client.force_login(self.user)

    def _ajax(self, url, data=None):
        return self.client.post(url, data or {}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def test_water_all_creates_checks_and_clears_reminders(self):
        Reminder.objects.create(user=self.user, plant=self.p1, kind="water",
                                message="Water", due_date=date.today())
        response = self._ajax(reverse("farm:quick_water_all"))
        self.assertEqual(response.json()["touched"], 2)
        self.assertTrue(DailyCheck.objects.filter(plant=self.p1, watered=True).exists())
        self.assertTrue(DailyCheck.objects.filter(plant=self.p2, watered=True).exists())
        self.assertTrue(Reminder.objects.get(plant=self.p1, kind="water", is_done=True).is_done)
        # Automation rolled the next watering occurrence over.
        self.assertTrue(Reminder.objects.filter(
            plant=self.p1, kind="water", is_done=False,
            due_date=date.today() + timedelta(days=self.p1.water_every_days)).exists())

    def test_water_area_scoped(self):
        response = self._ajax(reverse("farm:quick_water_all"), {"area": self.area.id})
        self.assertEqual(response.json()["touched"], 1)
        self.assertFalse(DailyCheck.objects.filter(plant=self.p2).exists())

    def test_fertilize_all(self):
        response = self._ajax(reverse("farm:quick_fertilize_all"))
        self.assertEqual(response.json()["touched"], 2)
        self.assertTrue(DailyCheck.objects.filter(plant=self.p1, fertilized=True).exists())

    def test_pest_quick_log(self):
        response = self._ajax(reverse("farm:quick_pest"), {"plant": self.p1.id})
        self.assertEqual(response.status_code, 200)
        log = CareLog.objects.get(plant=self.p1)
        self.assertEqual(log.category, "pest")

    def test_quick_log_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.post(reverse("farm:quick_water_all")).status_code, 302)

    def test_dashboard_shows_quick_log(self):
        self.assertContains(self.client.get(reverse("farm:dashboard")), "Quick log")

    def test_action_message_renders_as_toast(self):
        response = self.client.post(reverse("farm:quick_water_all"), follow=True)
        self.assertContains(response, "toast-container")
        self.assertContains(response, "Watered 2 plant(s)")

    def test_sidebar_badges_and_collapse(self):
        Reminder.objects.create(user=self.user, plant=self.p1,
                                kind="water", message="Water", due_date=date.today())
        response = self.client.get(reverse("farm:dashboard"))
        self.assertContains(response, "farmMenu")
        self.assertContains(response, "count-badge")

    def test_stats_ajax_counts(self):
        Reminder.objects.create(user=self.user, plant=self.p1,
                                kind="water", message="Water", due_date=date.today())
        data = self.client.get(reverse("farm:stats_ajax")).json()
        self.assertEqual(data, {"plant_count": 2, "due_count": 1, "ready_count": 0})

    def test_stats_ajax_scoped_per_user(self):
        other = get_user_model().objects.create_user(username="stat_other", password="secret1234")
        Plant.objects.create(user=other, name="Hidden", planting_date=date.today())
        data = self.client.get(reverse("farm:stats_ajax")).json()
        self.assertEqual(data["plant_count"], 2)

    def test_stats_ajax_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("farm:stats_ajax")).status_code, 302)

    def test_sidebar_farm_collapsed_off_farm(self):
        response = self.client.get(reverse("info:info_list"))
        self.assertContains(response, 'aria-expanded="false"')

    def test_login_history_link_admin_only(self):
        boss = get_user_model().objects.create_superuser(
            username="navboss", password="secret1234", email="n@example.com")
        self.client.force_login(boss)
        self.assertNotContains(self.client.get(reverse("dashboard")), "Login History")
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"))
        self.assertNotContains(response, "Login History")

    def test_area_create(self):
        response = self.client.post(reverse("farm:area_save_ajax"), {
            "name": "Bed A", "kind": "raised_bed", "rows": 4, "cols": 4,
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(GardenArea.objects.filter(user=self.user, name="Bed A").exists())

    def test_area_edit_and_delete(self):
        area = GardenArea.objects.create(user=self.user, name="Bed", rows=2, cols=2)
        response = self.client.post(reverse("farm:area_save_ajax"), {
            "id": area.id, "name": "Bed Renamed", "kind": "yard", "rows": 3, "cols": 3,
        })
        self.assertEqual(response.status_code, 200)
        area.refresh_from_db()
        self.assertEqual((area.name, area.rows), ("Bed Renamed", 3))
        plant = Plant.objects.create(user=self.user, name="Lettuce", area=area,
                                     planting_date=date.today())
        response = self.client.post(reverse("farm:area_delete_ajax", args=[area.id]))
        self.assertEqual(response.json()["status"], "deleted")
        plant.refresh_from_db()
        self.assertIsNone(plant.area)  # unplaced, not deleted

    def test_area_page_has_crud_buttons(self):
        response = self.client.get(reverse("farm:area_list"))
        self.assertContains(response, "deleteAreaModal")
        self.assertContains(response, "area_id")

    def test_generate_reminders_is_idempotent(self):
        plant = Plant.objects.create(user=self.user, name="Rambutan",
                                     planting_date=date.today())
        url = reverse("farm:plant_generate_reminders", args=[plant.id])
        first = self.client.post(url).json()["count"]
        second = self.client.post(url).json()["count"]
        self.assertEqual(first, 3)
        self.assertEqual(second, 0)
        self.assertEqual(plant.reminders.filter(is_done=False).count(), 3)

    def test_plant_list_provides_plot_picker_data(self):
        area = GardenArea.objects.create(user=self.user, name="Bed", rows=2, cols=3)
        Plant.objects.create(user=self.user, name="Lettuce", area=area,
                             pos_x=1, pos_y=0, planting_date=date.today())
        response = self.client.get(reverse("farm:plant_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bed (2×3")
        self.assertContains(response, "cellPicker")
        self.assertContains(response, "Lettuce")


def _fake_forecast_response(rain_mm_per_slot):
    """Build a fake urlopen context manager returning forecast JSON."""
    import io
    import json

    payload = {"list": [{"rain": {"3h": rain_mm_per_slot}} for _ in range(8)]}

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(payload).encode()

    return FakeResp()


class FarmWeatherTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.user = get_user_model().objects.create_user(username="weather", password="secret1234")

    def test_rain_sums_next_24h(self):
        from apps.farm import weather as farm_weather
        self.assertEqual(farm_weather.rain_next_24h({"list": [{"rain": {"3h": 2.0}}] * 8}), 16.0)
        self.assertEqual(farm_weather.rain_next_24h(None), 0.0)
        self.assertEqual(farm_weather.rain_next_24h({"list": []}), 0.0)

    def test_unconfigured_without_api_key(self):
        from django.test import override_settings
        from apps.farm import weather as farm_weather
        with override_settings(OPENWEATHER_API_KEY="", FARM_WEATHER_PROVIDER="openweathermap"):
            self.assertEqual(farm_weather.weather_status()["state"], "unconfigured")

    def test_heavy_rain_postpones_water_only(self):
        from unittest import mock
        from django.test import override_settings
        from apps.farm import weather as farm_weather
        plant = Plant.objects.create(user=self.user, name="Lettuce", planting_date=date.today())
        water = Reminder.objects.create(user=self.user, plant=plant, kind="water",
                                        message="Water the lettuce today", due_date=date.today())
        fert = Reminder.objects.create(user=self.user, plant=plant, kind="fertilize",
                                       message="Fertilize", due_date=date.today())
        with override_settings(OPENWEATHER_API_KEY="key", FARM_WEATHER_PROVIDER="openweathermap", FARM_RAIN_SKIP_MM=5.0):
            with mock.patch("urllib.request.urlopen", return_value=_fake_forecast_response(2.0)):
                result = farm_weather.adjust_water_reminders(self.user)
        self.assertTrue(result["skipped"])
        self.assertEqual(result["adjusted"], 1)
        water.refresh_from_db()
        fert.refresh_from_db()
        self.assertEqual(water.due_date, date.today() + timedelta(days=1))
        self.assertTrue(water.weather_paused)
        self.assertEqual(fert.due_date, date.today())  # untouched
        self.assertFalse(fert.weather_paused)

    def test_no_rain_leaves_reminders_alone(self):
        from unittest import mock
        from django.test import override_settings
        from apps.farm import weather as farm_weather
        plant = Plant.objects.create(user=self.user, name="Lettuce", planting_date=date.today())
        water = Reminder.objects.create(user=self.user, plant=plant, kind="water",
                                        message="Water", due_date=date.today())
        with override_settings(OPENWEATHER_API_KEY="key", FARM_WEATHER_PROVIDER="openweathermap", FARM_RAIN_SKIP_MM=5.0):
            with mock.patch("urllib.request.urlopen", return_value=_fake_forecast_response(0.0)):
                result = farm_weather.adjust_water_reminders(self.user)
        self.assertFalse(result["skipped"])
        water.refresh_from_db()
        self.assertEqual(water.due_date, date.today())

    def test_network_failure_fails_soft(self):
        from unittest import mock
        from django.test import override_settings
        from apps.farm import weather as farm_weather
        with override_settings(OPENWEATHER_API_KEY="key"):
            with mock.patch("urllib.request.urlopen", side_effect=OSError("offline")):
                self.assertEqual(farm_weather.weather_status()["state"], "unavailable")

    def test_weather_adjust_view(self):
        from unittest import mock
        from django.test import override_settings
        self.client.force_login(self.user)
        plant = Plant.objects.create(user=self.user, name="Okra", planting_date=date.today())
        Reminder.objects.create(user=self.user, plant=plant, kind="water",
                                message="Water the okra today", due_date=date.today())
        with override_settings(OPENWEATHER_API_KEY="key", FARM_WEATHER_PROVIDER="openweathermap", FARM_RAIN_SKIP_MM=5.0):
            with mock.patch("urllib.request.urlopen", return_value=_fake_forecast_response(3.0)):
                response = self.client.post(reverse("farm:weather_adjust"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Reminder.objects.filter(plant=plant, weather_paused=True).exists())


def _fake_open_meteo_response(mm_per_hour, start=None):
    """Build a fake urlopen context manager returning Open-Meteo hourly JSON."""
    import io
    import json
    from datetime import datetime, timezone as dt_timezone

    start = start or datetime.now(dt_timezone.utc).replace(minute=0, second=0, microsecond=0)
    times = [(start + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(48)]
    payload = {"hourly": {"time": times, "precipitation": [mm_per_hour] * 48}}

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(payload).encode()

    return FakeResp()


class FarmOpenMeteoTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.user = get_user_model().objects.create_user(username="meteo", password="secret1234")

    def test_hourly_rain_sums_next_24h_only(self):
        from datetime import datetime, timezone as dt_timezone
        from apps.farm import weather as farm_weather
        now = datetime.now(dt_timezone.utc).replace(minute=0, second=0, microsecond=0)
        payload = {
            "hourly": {
                "time": [(now + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(48)],
                "precipitation": [1.0] * 48,
            }
        }
        self.assertEqual(farm_weather.rain_next_24h_open_meteo(payload, now=now), 24.0)
        self.assertEqual(farm_weather.rain_next_24h_open_meteo(None), 0.0)
        self.assertEqual(farm_weather.rain_next_24h_open_meteo({}), 0.0)

    def test_status_ok_without_api_key(self):
        from unittest import mock
        from apps.farm import weather as farm_weather
        with mock.patch("urllib.request.urlopen", return_value=_fake_open_meteo_response(0.0)):
            status = farm_weather.weather_status()
        self.assertEqual(status["state"], "ok")
        self.assertFalse(status["skip_watering"])

    def test_heavy_rain_postpones_via_open_meteo(self):
        from unittest import mock
        from django.test import override_settings
        from apps.farm import weather as farm_weather
        plant = Plant.objects.create(user=self.user, name="Lettuce", planting_date=date.today())
        water = Reminder.objects.create(user=self.user, plant=plant, kind="water",
                                        message="Water", due_date=date.today())
        with override_settings(FARM_WEATHER_PROVIDER="open-meteo", FARM_RAIN_SKIP_MM=5.0):
            with mock.patch("urllib.request.urlopen", return_value=_fake_open_meteo_response(1.0)):
                result = farm_weather.adjust_water_reminders(self.user)
        self.assertTrue(result["skipped"])
        self.assertEqual(result["adjusted"], 1)
        water.refresh_from_db()
        self.assertTrue(water.weather_paused)

    def test_hourly_slots_from_payload(self):
        import json
        from datetime import datetime, timezone as dt_timezone
        from apps.farm import weather as farm_weather
        now = datetime.now(dt_timezone.utc).replace(minute=0, second=0, microsecond=0)
        payload = {
            "hourly": {
                "time": [(now + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(48)],
                "precipitation": [2.0] * 48,
            }
        }
        slots = farm_weather.hourly_next_24h_open_meteo(payload, now=now)
        self.assertEqual(len(slots), 24)
        self.assertTrue(all(s["mm"] == 2.0 for s in slots))
        self.assertTrue(all(s["h"] == 100 for s in slots))
        self.assertEqual(farm_weather.hourly_next_24h_open_meteo(None), [])
        self.assertEqual(farm_weather.hourly_next_24h_open_meteo({}), [])

    def test_status_includes_hourly(self):
        from unittest import mock
        from apps.farm import weather as farm_weather
        with mock.patch("urllib.request.urlopen", return_value=_fake_open_meteo_response(0.5)):
            status = farm_weather.weather_status()
        self.assertEqual(status["state"], "ok")
        self.assertEqual(len(status["hourly"]), 24)

    def test_refresh_clears_cache(self):
        from django.core.cache import cache
        from apps.farm import weather as farm_weather
        self.client.force_login(self.user)
        cache.set(farm_weather.METEO_CACHE_KEY, {"hourly": {}}, 1800)
        response = self.client.post(reverse("farm:weather_refresh"))
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(cache.get(farm_weather.METEO_CACHE_KEY))


class FarmGeminiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="gemini", password="secret1234")

    def _plant(self):
        return Plant.objects.create(user=self.user, name="Tomato", variety="Cherry",
                                    planting_date=date.today() - timedelta(days=30))

    def test_prompt_contains_plant_context(self):
        from apps.farm import ai_advice as gemini
        plant = self._plant()
        prompt = gemini.build_prompt(plant, [], [], {"state": "unavailable"})
        self.assertIn("Tomato", prompt)
        self.assertIn(str(plant.expected_harvest_date), prompt)
        self.assertIn("Harvest estimate", prompt)

    def test_unconfigured_returns_error(self):
        from django.test import override_settings
        from apps.farm import ai_advice as gemini
        with override_settings(GEMINI_API_KEY=""):
            result = gemini.ask_gemini("hello")
        self.assertFalse(result["ok"])
        self.assertIn("GEMINI_API_KEY", result["error"])

    def test_success_parses_answer(self):
        import json
        from unittest import mock
        from django.test import override_settings
        from apps.farm import ai_advice as gemini

        payload = {"candidates": [{"content": {"parts": [{"text": "Water daily."}]}}]}

        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps(payload).encode()

        with override_settings(GEMINI_API_KEY="key"):
            with mock.patch("urllib.request.urlopen", return_value=FakeResp()):
                result = gemini.ask_gemini("hello")
        self.assertTrue(result["ok"])
        self.assertEqual(result["text"], "Water daily.")

    def test_network_failure_fails_soft(self):
        from unittest import mock
        from django.test import override_settings
        from apps.farm import ai_advice as gemini
        with override_settings(GEMINI_API_KEY="key"):
            with mock.patch("urllib.request.urlopen", side_effect=OSError("offline")):
                result = gemini.ask_gemini("hello")
        self.assertFalse(result["ok"])

    def test_view_requires_key(self):
        plant = self._plant()
        self.client.force_login(self.user)
        response = self.client.post(reverse("farm:ai_advice_ajax", args=[plant.id]))
        self.assertEqual(response.status_code, 400)

    def test_view_saves_advice_to_care_history(self):
        import json
        from unittest import mock
        from django.test import override_settings
        plant = self._plant()
        self.client.force_login(self.user)
        payload = {"candidates": [{"content": {"parts": [{"text": "Mulch the base."}]}}]}

        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps(payload).encode()

        with override_settings(GEMINI_API_KEY="key"):
            with mock.patch("urllib.request.urlopen", return_value=FakeResp()):
                response = self.client.post(reverse("farm:ai_advice_ajax", args=[plant.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CareLog.objects.filter(plant=plant, description__contains="Mulch").exists())

    def test_view_scoped_to_owner(self):
        other = get_user_model().objects.create_user(username="gemini_other", password="secret1234")
        plant = self._plant()
        self.client.force_login(other)
        response = self.client.post(reverse("farm:ai_advice_ajax", args=[plant.id]))
        self.assertEqual(response.status_code, 404)


class FarmOpenRouterTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="orouter", password="secret1234")

    def _fake_response(self, payload):
        import json

        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps(payload).encode()

        return FakeResp()

    def test_unconfigured_returns_error(self):
        from django.test import override_settings
        from apps.farm import ai_openrouter as orouter
        with override_settings(OPENROUTER_API_KEY=""):
            result = orouter.ask_openrouter("hello")
        self.assertFalse(result["ok"])
        self.assertIn("OPENROUTER_API_KEY", result["error"])

    def test_success_parses_answer(self):
        from unittest import mock
        from django.test import override_settings
        from apps.farm import ai_openrouter as orouter
        payload = {"choices": [{"message": {"content": "  Water at dawn. "}}]}
        with override_settings(OPENROUTER_API_KEY="key"):
            with mock.patch("urllib.request.urlopen", return_value=self._fake_response(payload)):
                result = orouter.ask_openrouter("hello")
        self.assertTrue(result["ok"])
        self.assertEqual(result["text"], "Water at dawn.")

    def test_api_error_payload(self):
        from unittest import mock
        from django.test import override_settings
        from apps.farm import ai_openrouter as orouter
        payload = {"error": {"message": "No credits left"}}
        with override_settings(OPENROUTER_API_KEY="key"):
            with mock.patch("urllib.request.urlopen", return_value=self._fake_response(payload)):
                result = orouter.ask_openrouter("hello")
        self.assertFalse(result["ok"])
        self.assertIn("No credits", result["error"])

    def test_view_uses_openrouter_when_selected(self):
        import json
        from unittest import mock
        from django.test import override_settings
        plant = Plant.objects.create(user=self.user, name="Lettuce", planting_date=date.today())
        self.client.force_login(self.user)
        payload = {"choices": [{"message": {"content": "Mulch the rows."}}]}
        with override_settings(AI_PROVIDER="openrouter", OPENROUTER_API_KEY="key"):
            with mock.patch("urllib.request.urlopen", return_value=self._fake_response(payload)):
                response = self.client.post(reverse("farm:ai_advice_ajax", args=[plant.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["advice"], "Mulch the rows.")
        self.assertTrue(CareLog.objects.filter(plant=plant, description__contains="OpenRouter").exists())

    def test_view_requires_openrouter_key(self):
        from django.test import override_settings
        plant = Plant.objects.create(user=self.user, name="Lettuce", planting_date=date.today())
        self.client.force_login(self.user)
        with override_settings(AI_PROVIDER="openrouter", OPENROUTER_API_KEY=""):
            response = self.client.post(reverse("farm:ai_advice_ajax", args=[plant.id]))
        self.assertEqual(response.status_code, 400)


class FarmHarvestAuditTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="auditor", password="secret1234")
        self.client.force_login(self.user)

    def _plant(self, **overrides):
        values = {
            "user": self.user,
            "name": "Tomato",
            "variety": "Cherry",
            "planting_date": date.today() - timedelta(days=30),
            "start_method": "transplant",
            "days_to_harvest": 75,
        }
        values.update(overrides)
        return Plant.objects.create(**values)

    def _fake_response(self, text):
        import json

        payload = {"candidates": [{"content": {"parts": [{"text": text}]}}]}

        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps(payload).encode()

        return FakeResp()

    def test_prompt_includes_method_and_catalog(self):
        from apps.farm import ai_advice as gemini
        plant = self._plant()
        prompt = gemini.build_harvest_audit_prompt([plant])
        self.assertIn('"start_method":"transplant"', prompt)
        self.assertIn('"days_to_harvest":75', prompt)
        self.assertIn('"catalog_min_days":65', prompt)
        self.assertIn('"catalog_max_days":85', prompt)
        self.assertIn("Cherry", prompt)

    def test_prompt_includes_tree_crop_multi_year_context(self):
        from apps.farm import ai_advice as gemini
        plant = self._plant(
            name="Rambutan", variety="",
            start_method="transplant", days_to_harvest=1095,
        )
        prompt = gemini.build_harvest_audit_prompt([plant])
        self.assertIn("Tree crops legitimately need multi-year estimates", prompt)
        self.assertIn('"catalog_suggested_days":1095', prompt)
        self.assertIn('"catalog_min_days":730', prompt)
        self.assertIn('"catalog_max_days":1460', prompt)

    def test_parser_accepts_fenced_json(self):
        import json
        from apps.farm import ai_advice as gemini
        payload = [{
            "id": 7,
            "verdict": "too late",
            "suggested_days": "45 days",
            "reason": "Lettuce matures faster.",
        }]
        parsed = gemini.parse_harvest_audit("```json\n" + json.dumps(payload) + "\n```")
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["id"], 7)
        self.assertEqual(parsed[0]["verdict"], "too_late")
        self.assertEqual(parsed[0]["suggested_days"], 45)

    def test_single_check_returns_audit_row(self):
        import json
        from unittest import mock
        from django.test import override_settings
        plant = self._plant()
        answer = json.dumps([{
            "id": plant.id,
            "verdict": "ok",
            "suggested_days": None,
            "reason": "Within the transplant window.",
        }])
        with override_settings(GEMINI_API_KEY="key"):
            with mock.patch("urllib.request.urlopen", return_value=self._fake_response(answer)):
                response = self.client.post(reverse("farm:harvest_check_ajax", args=[plant.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["checked"], 1)
        self.assertEqual(data["rows"][0]["current_days"], 75)
        self.assertEqual(data["rows"][0]["current_basis"], "from transplant")
        self.assertEqual(data["rows"][0]["catalog_min"], 65)
        self.assertEqual(data["rows"][0]["verdict"], "ok")
        self.assertFalse(CareLog.objects.filter(plant=plant).exists())

    def test_single_check_requires_key(self):
        from django.test import override_settings
        plant = self._plant()
        with override_settings(GEMINI_API_KEY=""):
            response = self.client.post(reverse("farm:harvest_check_ajax", args=[plant.id]))
        self.assertEqual(response.status_code, 400)

    def test_single_check_scoped_to_owner(self):
        other = get_user_model().objects.create_user(username="auditor_other", password="secret1234")
        plant = self._plant()
        self.client.force_login(other)
        response = self.client.post(reverse("farm:harvest_check_ajax", args=[plant.id]))
        self.assertEqual(response.status_code, 404)

    def test_all_check_checks_only_visible_plants(self):
        import json
        from unittest import mock
        from django.test import override_settings
        lettuce = self._plant(name="Lettuce", variety="", start_method="direct",
                              days_to_harvest=60)
        tomato = self._plant(name="Tomato", days_to_harvest=75)
        other = get_user_model().objects.create_user(username="auditor_other2", password="secret1234")
        hidden = Plant.objects.create(user=other, name="Rambutan", planting_date=date.today())
        answer = json.dumps([
            {"id": lettuce.id, "verdict": "too_late", "suggested_days": 45,
             "reason": "Typical lettuce is 30-55 days."},
            {"id": tomato.id, "verdict": "ok", "suggested_days": None,
             "reason": "Within the transplant window."},
            {"id": hidden.id, "verdict": "ok", "suggested_days": None,
             "reason": "Should be ignored."},
        ])
        with override_settings(GEMINI_API_KEY="key"):
            with mock.patch(
                "apps.farm.ai_advice.ask_gemini",
                return_value={"ok": True, "text": answer},
            ) as ask:
                response = self.client.post(reverse("farm:harvest_check_all_ajax"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["checked"], 2)
        self.assertEqual({row["id"] for row in data["rows"]}, {lettuce.id, tomato.id})
        prompt = ask.call_args[0][0]
        self.assertIn("Lettuce", prompt)
        self.assertIn("Tomato", prompt)
        self.assertNotIn("Rambutan", prompt)

    def test_all_check_without_plants_returns_400(self):
        response = self.client.post(reverse("farm:harvest_check_all_ajax"))
        self.assertEqual(response.status_code, 400)

    def test_unstructured_answer_is_returned_raw(self):
        from unittest import mock
        from django.test import override_settings
        plant = self._plant()
        with override_settings(GEMINI_API_KEY="key"):
            with mock.patch(
                "apps.farm.ai_advice.ask_gemini",
                return_value={"ok": True, "text": "Looks fine to me."},
            ):
                response = self.client.post(reverse("farm:harvest_check_ajax", args=[plant.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["rows"], [])
        self.assertEqual(data["raw"], "Looks fine to me.")

    def test_harvest_check_uses_openrouter_when_selected(self):
        import json
        from unittest import mock
        from django.test import override_settings
        plant = self._plant()
        answer = json.dumps([{
            "id": plant.id,
            "verdict": "ok",
            "suggested_days": None,
            "reason": "Within range.",
        }])
        with override_settings(AI_PROVIDER="openrouter", OPENROUTER_API_KEY="key"):
            with mock.patch(
                "apps.farm.ai_openrouter.ask_openrouter",
                return_value={"ok": True, "text": answer},
            ):
                response = self.client.post(reverse("farm:harvest_check_ajax", args=[plant.id]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("OpenRouter", response.json()["backend"])


class FarmMapGridTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="mapper", password="secret1234")
        self.area = GardenArea.objects.create(user=self.user, name="Bed", rows=2, cols=3)
        self.client.force_login(self.user)

    def test_grid_places_plant_and_empty_cells(self):
        Plant.objects.create(user=self.user, name="Lettuce", area=self.area,
                             pos_x=1, pos_y=0, planting_date=date.today())
        response = self.client.get(reverse("farm:map"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertContains(response, "Lettuce")
        # 2x3 = 6 cells, 1 filled -> 5 empty markers
        self.assertEqual(content.count("· empty ·"), 5)

    def test_off_grid_plant_listed_as_overflow(self):
        Plant.objects.create(user=self.user, name="Tomato", area=self.area,
                             pos_x=9, pos_y=9, planting_date=date.today())
        response = self.client.get(reverse("farm:map"))
        self.assertContains(response, "Off-grid")

    def test_auto_arrange_places_unplaced(self):
        from apps.farm.companion import find_spot
        Plant.objects.create(user=self.user, name="Okra", planting_date=date.today())
        response = self.client.post(
            reverse("farm:map_auto_arrange"), {},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.json()["placed"], 1)
        okra = Plant.objects.get(name="Okra")
        self.assertEqual(okra.area, self.area)
        self.assertContains(self.client.get(reverse("farm:map")), "Auto-arrange")

    def test_auto_arrange_avoids_bad_neighbor(self):
        Plant.objects.create(user=self.user, name="Tomato", area=self.area,
                             pos_x=0, pos_y=0, planting_date=date.today())
        potato = Plant.objects.create(user=self.user, name="Potato",
                                      planting_date=date.today())
        self.client.post(reverse("farm:map_auto_arrange"))
        potato.refresh_from_db()
        # (1,0) is empty but adjacent to tomato -> must not be chosen
        self.assertNotEqual((potato.pos_x, potato.pos_y), (1, 0))
        self.assertEqual(potato.area, self.area)

    def test_auto_arrange_full_plot_skips(self):
        Plant.objects.create(user=self.user, name="A", area=self.area,
                             pos_x=0, pos_y=0, planting_date=date.today())
        Plant.objects.create(user=self.user, name="B", area=self.area,
                             pos_x=1, pos_y=0, planting_date=date.today())
        Plant.objects.create(user=self.user, name="C", area=self.area,
                             pos_x=2, pos_y=0, planting_date=date.today())
        Plant.objects.create(user=self.user, name="D", area=self.area,
                             pos_x=0, pos_y=1, planting_date=date.today())
        Plant.objects.create(user=self.user, name="E", area=self.area,
                             pos_x=1, pos_y=1, planting_date=date.today())
        Plant.objects.create(user=self.user, name="F", area=self.area,
                             pos_x=2, pos_y=1, planting_date=date.today())
        Plant.objects.create(user=self.user, name="Extra", planting_date=date.today())
        response = self.client.post(
            reverse("farm:map_auto_arrange"), {},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.json(), {"status": "success", "placed": 0, "skipped": 1})

    def test_unplaced_plant_section(self):
        Plant.objects.create(user=self.user, name="Okra", planting_date=date.today())
        response = self.client.get(reverse("farm:map"))
        self.assertContains(response, "Unplaced plants")

    def test_move_plant_within_plot(self):
        plant = Plant.objects.create(user=self.user, name="Lettuce", area=self.area,
                                     pos_x=0, pos_y=0, planting_date=date.today())
        response = self.client.post(reverse("farm:plant_move_ajax", args=[plant.id]), {
            "area": self.area.id, "pos_x": 2, "pos_y": 1,
        })
        self.assertEqual(response.json()["status"], "moved")
        plant.refresh_from_db()
        self.assertEqual((plant.pos_x, plant.pos_y), (2, 1))

    def test_move_plant_across_plots(self):
        other = GardenArea.objects.create(user=self.user, name="Other", rows=2, cols=2)
        plant = Plant.objects.create(user=self.user, name="Lettuce", area=self.area,
                                     pos_x=0, pos_y=0, planting_date=date.today())
        self.client.post(reverse("farm:plant_move_ajax", args=[plant.id]), {
            "area": other.id, "pos_x": 1, "pos_y": 1,
        })
        plant.refresh_from_db()
        self.assertEqual(plant.area, other)

    def test_move_rejects_out_of_bounds(self):
        plant = Plant.objects.create(user=self.user, name="Lettuce", area=self.area,
                                     pos_x=0, pos_y=0, planting_date=date.today())
        response = self.client.post(reverse("farm:plant_move_ajax", args=[plant.id]), {
            "area": self.area.id, "pos_x": 9, "pos_y": 9,
        })
        self.assertEqual(response.status_code, 400)

    def test_move_other_users_plant_blocked(self):
        other = get_user_model().objects.create_user(username="mover_other", password="secret1234")
        plant = Plant.objects.create(user=other, name="Lettuce", area=self.area,
                                     pos_x=0, pos_y=0, planting_date=date.today())
        other_area = GardenArea.objects.create(user=other, name="O", rows=2, cols=2)
        plant.area = other_area
        plant.save()
        response = self.client.post(reverse("farm:plant_move_ajax", args=[plant.id]), {
            "area": self.area.id, "pos_x": 1, "pos_y": 1,
        })
        self.assertEqual(response.status_code, 404)

    def test_map_shows_need_badges(self):
        plant = Plant.objects.create(user=self.user, name="Lettuce", area=self.area,
                                     pos_x=0, pos_y=0, planting_date=date.today())
        Reminder.objects.create(user=self.user, plant=plant, kind="water",
                                message="Water", due_date=date.today() - timedelta(days=2))
        Reminder.objects.create(user=self.user, plant=plant, kind="fertilize",
                                message="Fertilize", due_date=date.today() + timedelta(days=5))
        response = self.client.get(reverse("farm:map"))
        self.assertContains(response, 'data-need="water"')
        self.assertContains(response, 'data-need="fertilize"')
        self.assertContains(response, "1 overdue")
        self.assertNotContains(response, 'data-need="harvest"')


class FarmCompanionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="companion", password="secret1234")
        self.area = GardenArea.objects.create(user=self.user, name="Bed", rows=3, cols=3)
        self.client.force_login(self.user)

    def test_bad_neighbors_flagged(self):
        from apps.farm.companion import analyze
        tomato = Plant.objects.create(user=self.user, name="Tomato", area=self.area,
                                      pos_x=0, pos_y=0, planting_date=date.today())
        potato = Plant.objects.create(user=self.user, name="Potatoes", area=self.area,
                                      pos_x=1, pos_y=0, planting_date=date.today())
        alerts = analyze([tomato, potato])
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["kind"], "bad")
        self.assertIn("blight", alerts[0]["reason"])

    def test_good_pairing_highlighted(self):
        from apps.farm.companion import pairing
        kind, reason = pairing("Marigolds", "TOMATO")
        self.assertEqual(kind, "good")
        self.assertIn("aphids", reason)

    def test_distant_plants_ignored(self):
        from apps.farm.companion import analyze
        tomato = Plant.objects.create(user=self.user, name="Tomato", area=self.area,
                                      pos_x=0, pos_y=0, planting_date=date.today())
        basil = Plant.objects.create(user=self.user, name="Basil", area=self.area,
                                     pos_x=2, pos_y=2, planting_date=date.today())
        self.assertEqual(analyze([tomato, basil]), [])

    def test_map_shows_alerts_and_badges(self):
        Plant.objects.create(user=self.user, name="Tomato", area=self.area,
                             pos_x=0, pos_y=0, planting_date=date.today())
        Plant.objects.create(user=self.user, name="Marigold", area=self.area,
                             pos_x=0, pos_y=1, planting_date=date.today())
        Plant.objects.create(user=self.user, name="Potato", area=self.area,
                             pos_x=1, pos_y=0, planting_date=date.today())
        response = self.client.get(reverse("farm:map"))
        self.assertContains(response, "⚠️")
        self.assertContains(response, "✨")
        self.assertContains(response, "blight")
        self.assertContains(response, "Marigold")


class FarmAdminOversightTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="overseer", password="secret1234", email="o@example.com")
        self.staff = get_user_model().objects.create_user(username="worker", password="secret1234")
        self.plant = Plant.objects.create(user=self.staff, name="Lettuce",
                                          planting_date=date.today())

    def test_admin_sees_staff_plant(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("farm:plant_list")), "Lettuce")
        self.assertEqual(
            self.client.get(reverse("farm:plant_detail", args=[self.plant.id])).status_code, 200)

    def test_staff_cannot_see_admin_plant(self):
        Plant.objects.create(user=self.admin, name="Secret Herb", planting_date=date.today())
        self.client.force_login(self.staff)
        self.assertNotContains(self.client.get(reverse("farm:plant_list")), "Secret Herb")

    def test_admin_edit_keeps_owner(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("farm:plant_save_ajax"), {
            "id": self.plant.id, "name": "Lettuce", "planting_date": date.today().isoformat(),
        })
        self.assertEqual(response.status_code, 200)
        self.plant.refresh_from_db()
        self.assertEqual(self.plant.user, self.staff)

    def test_admin_can_delete_staff_care_log(self):
        log = CareLog.objects.create(user=self.staff, plant=self.plant,
                                     date=date.today(), category="note", description="x")
        self.client.force_login(self.admin)
        response = self.client.post(reverse("farm:carelog_delete_ajax", args=[log.id]))
        self.assertEqual(response.status_code, 200)


class FarmDeadPlantTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="undertaker", password="secret1234")
        self.client.force_login(self.user)

    def test_marking_dead_creates_reminder(self):
        plant = Plant.objects.create(user=self.user, name="Lettuce", planting_date=date.today())
        response = self.client.post(reverse("farm:plant_save_ajax"), {
            "id": plant.id, "name": "Lettuce",
            "planting_date": date.today().isoformat(), "status": "dead",
        })
        self.assertEqual(response.status_code, 200)
        reminder = Reminder.objects.get(user=self.user, plant=plant, kind="custom")
        self.assertIn("dead", reminder.message)
        self.assertEqual(reminder.due_date, date.today())
        self.assertFalse(reminder.is_done)

    def test_dead_reminder_is_idempotent(self):
        plant = Plant.objects.create(user=self.user, name="Lettuce", planting_date=date.today())
        url_data = {"id": plant.id, "name": "Lettuce",
                    "planting_date": date.today().isoformat(), "status": "dead"}
        self.client.post(reverse("farm:plant_save_ajax"), url_data)
        self.client.post(reverse("farm:plant_save_ajax"), url_data)
        self.assertEqual(
            Reminder.objects.filter(user=self.user, plant=plant, kind="custom").count(), 1)

    def test_non_dead_update_creates_nothing(self):
        plant = Plant.objects.create(user=self.user, name="Lettuce", planting_date=date.today())
        self.client.post(reverse("farm:plant_save_ajax"), {
            "id": plant.id, "name": "Lettuce",
            "planting_date": date.today().isoformat(), "status": "growing",
        })
        self.assertFalse(Reminder.objects.filter(plant=plant, kind="custom").exists())

    def test_poor_health_check_warns(self):
        plant = Plant.objects.create(user=self.user, name="Okra", planting_date=date.today())
        response = self.client.post(reverse("farm:dailycheck_save_ajax", args=[plant.id]), {
            "date": date.today().isoformat(), "health": "poor",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Reminder.objects.filter(
            plant=plant, kind="custom", message__icontains="struggling").exists())
        # Second poor check must not duplicate the open reminder.
        self.client.post(reverse("farm:dailycheck_save_ajax", args=[plant.id]), {
            "date": (date.today() + timedelta(days=1)).isoformat(), "health": "poor",
        })
        self.assertEqual(Reminder.objects.filter(
            plant=plant, kind="custom", message__icontains="struggling").count(), 1)

    def test_poor_check_on_dead_plant_skipped(self):
        plant = Plant.objects.create(user=self.user, name="Okra", status="dead",
                                     planting_date=date.today())
        self.client.post(reverse("farm:dailycheck_save_ajax", args=[plant.id]), {
            "date": date.today().isoformat(), "health": "poor",
        })
        self.assertFalse(Reminder.objects.filter(
            plant=plant, message__icontains="struggling").exists())


class FarmPlantEditSyncTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="editor", password="secret1234")
        self.client.force_login(self.user)
        self.plant = Plant.objects.create(user=self.user, name="Lettuce",
                                          planting_date=date.today(),
                                          days_to_harvest=45, water_every_days=1,
                                          fertilize_every_days=14)
        Reminder.objects.bulk_create(Reminder.build_defaults_for_plant(self.plant))
        self.custom = Reminder.objects.create(
            user=self.user, plant=self.plant, kind="custom",
            message="Lettuce: call supplier", due_date=date.today())
        self.done = Reminder.objects.create(
            user=self.user, plant=self.plant, kind="water", is_done=True,
            message="Water the lettuce today", due_date=date.today())

    def _edit(self, **fields):
        data = {"id": self.plant.id, "name": self.plant.name,
                "planting_date": self.plant.planting_date.isoformat()}
        data.update(fields)
        return self.client.post(reverse("farm:plant_save_ajax"), data)

    def test_rename_updates_open_auto_reminders(self):
        response = self._edit(name="LettuceX")
        self.assertEqual(response.status_code, 200)
        messages = set(Reminder.objects.filter(
            plant=self.plant, is_done=False,
            kind__in=["water", "fertilize", "harvest"],
        ).values_list("message", flat=True))
        self.assertTrue(messages)
        self.assertTrue(all("lettucex" in m for m in messages))
        # Custom + done reminders keep the old text.
        self.custom.refresh_from_db()
        self.done.refresh_from_db()
        self.assertIn("Lettuce", self.custom.message)
        self.assertIn("lettuce", self.done.message)

    def test_reschedule_moves_harvest_reminder(self):
        old_expected = self.plant.expected_harvest_date
        new_date = (date.today() - timedelta(days=20)).isoformat()
        response = self._edit(planting_date=new_date)
        self.assertEqual(response.status_code, 200)
        self.plant.refresh_from_db()
        harvest = Reminder.objects.get(plant=self.plant, kind="harvest", is_done=False)
        self.assertEqual(harvest.due_date, self.plant.expected_harvest_date)
        self.assertNotEqual(self.plant.expected_harvest_date, old_expected)
        self.assertIn(str(self.plant.expected_harvest_date), harvest.message)
        # Water reminder keeps its own due date.
        water = Reminder.objects.get(plant=self.plant, kind="water", is_done=False)
        self.assertNotEqual(water.due_date, self.plant.expected_harvest_date)

    def test_manually_moved_harvest_keeps_due_date(self):
        harvest = Reminder.objects.get(plant=self.plant, kind="harvest", is_done=False)
        harvest.due_date = date.today() + timedelta(days=90)
        harvest.save()
        self._edit(planting_date=(date.today() - timedelta(days=20)).isoformat())
        harvest.refresh_from_db()
        self.assertEqual(harvest.due_date, date.today() + timedelta(days=90))

    def test_noop_edit_touches_nothing(self):
        before = list(Reminder.objects.filter(plant=self.plant).values_list("id", "message", "due_date"))
        response = self._edit()
        self.assertEqual(response.json()["synced"], 0)
        after = list(Reminder.objects.filter(plant=self.plant).values_list("id", "message", "due_date"))
        self.assertEqual(before, after)

    def test_fertilize_interval_moves_auto_reminder(self):
        fert = Reminder.objects.get(plant=self.plant, kind="fertilize", is_done=False)
        anchor = self.plant.created_at.date()
        self.assertEqual(fert.due_date, anchor + timedelta(days=14))
        response = self._edit(fertilize_every_days="7")
        self.assertEqual(response.status_code, 200)
        fert.refresh_from_db()
        self.assertEqual(fert.due_date, anchor + timedelta(days=7))

    def test_fertilize_manually_moved_keeps_due_date(self):
        fert = Reminder.objects.get(plant=self.plant, kind="fertilize", is_done=False)
        fert.due_date = date.today() + timedelta(days=60)
        fert.save()
        self._edit(fertilize_every_days="7")
        fert.refresh_from_db()
        self.assertEqual(fert.due_date, date.today() + timedelta(days=60))

    def test_water_interval_moves_auto_reminder(self):
        water = Reminder.objects.get(plant=self.plant, kind="water", is_done=False)
        anchor = self.plant.created_at.date()
        self.assertEqual(water.due_date, anchor + timedelta(days=1))
        self._edit(water_every_days="3")
        water.refresh_from_db()
        self.assertEqual(water.due_date, anchor + timedelta(days=3))


class FarmRolloverTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="rolo", password="secret1234")
        self.client.force_login(self.user)
        self.plant = Plant.objects.create(user=self.user, name="Lettuce",
                                          planting_date=date.today(),
                                          days_to_harvest=45, water_every_days=2,
                                          fertilize_every_days=14)

    def test_toggle_done_rolls_next_water(self):
        rem = Reminder.objects.create(user=self.user, plant=self.plant, kind="water",
                                      message="Water", due_date=date.today())
        response = self.client.post(reverse("farm:reminder_toggle_ajax", args=[rem.id]))
        self.assertTrue(response.json()["is_done"])
        nxt = Reminder.objects.get(plant=self.plant, kind="water", is_done=False)
        self.assertNotEqual(nxt.id, rem.id)
        self.assertEqual(nxt.due_date, date.today() + timedelta(days=2))

    def test_toggle_rolls_only_when_none_open(self):
        Reminder.objects.create(user=self.user, plant=self.plant, kind="water",
                                message="old", due_date=date.today())
        future = Reminder.objects.create(user=self.user, plant=self.plant, kind="water",
                                         message="future", due_date=date.today() + timedelta(days=9))
        rem = Reminder.objects.filter(kind="water", is_done=False).order_by("due_date").first()
        self.client.post(reverse("farm:reminder_toggle_ajax", args=[rem.id]))
        self.assertEqual(Reminder.objects.filter(
            plant=self.plant, kind="water", is_done=False).count(), 1)
        future.refresh_from_db()
        self.assertFalse(future.is_done)

    def test_harvest_never_rolls_over(self):
        rem = Reminder.objects.create(user=self.user, plant=self.plant, kind="harvest",
                                      message="Harvest", due_date=date.today())
        self.client.post(reverse("farm:reminder_toggle_ajax", args=[rem.id]))
        self.assertFalse(Reminder.objects.filter(
            plant=self.plant, kind="harvest", is_done=False).exists())

    def test_daily_check_watered_rolls_over(self):
        Reminder.objects.create(user=self.user, plant=self.plant, kind="water",
                                message="Water", due_date=date.today())
        self.client.post(reverse("farm:dailycheck_save_ajax", args=[self.plant.id]), {
            "date": date.today().isoformat(), "watered": "true", "health": "good",
        })
        self.assertTrue(Reminder.objects.filter(
            plant=self.plant, kind="water", is_done=False,
            due_date=date.today() + timedelta(days=2)).exists())

    def test_sync_command_ensures_and_resyncs(self):
        from django.core.management import call_command
        from io import StringIO
        # Plant with no reminders + stale harvest date.
        lonely = Plant.objects.create(user=self.user, name="Okra", planting_date=date.today())
        stale = Reminder.objects.create(user=self.user, plant=lonely, kind="harvest",
                                        message=f"Harvest the okra around {date.today()}",
                                        due_date=date.today())
        out = StringIO()
        call_command("sync_reminders", stdout=out)
        self.assertIn("sync complete", out.getvalue())
        self.assertTrue(Reminder.objects.filter(
            plant=lonely, kind="water", is_done=False).exists())
        stale.refresh_from_db()
        self.assertEqual(stale.due_date, lonely.expected_harvest_date)
