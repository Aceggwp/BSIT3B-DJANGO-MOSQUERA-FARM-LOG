"""Crop maturity data used by the harvest automation.

The numbers are planning ranges, not guarantees. They are based on common
extension/seed-guide maturity windows for each crop. A plant's actual harvest
date still depends on the variety, temperature, day length, water, nutrients,
pests, and disease.

Two start methods are supported because maturity is counted differently:

* ``direct``     - the planting date is the sowing date; days are counted from
                    sowing.
* ``transplant`` - the planting date is the date seedlings went into the
                    garden; days are counted from transplanting.

Tomato, pepper, eggplant, cabbage, broccoli, cauliflower, and bitter gourd are
normally transplanted. Root, leafy, bean, cucumber, and okra crops are normally
direct sown in the garden. Each crop has a recommended default, but the grower
can choose the other method and the estimate adjusts automatically.

Perennial fruit crops use much longer windows. For fruit trees, ``direct``
means seed-grown in place, while ``transplant`` means a grafted, marcotted, or
nursery-raised planting material. Papaya and banana are short-lived perennials;
banana is normally planted from a sucker or tissue-culture plantlet, so
``transplant`` is its normal method.
"""

from __future__ import annotations

import re

START_METHODS = ("direct", "transplant")
START_METHOD_LABELS = {
    "direct": "from sowing",
    "transplant": "from transplant",
}

# Each profile has:
#   label               - display name
#   aliases             - alternate names/plurals/local names
#   default_method      - "direct" or "transplant"
#   days                - suggested whole-day estimate per start method
#   ranges              - typical min/max days per start method
#   water_every_days    - default watering interval
#   fertilize_every_days - default fertilizing interval
#   note                - short caveat shown in the UI
CROP_CATALOG = {
    "lettuce": {
        "label": "Lettuce",
        "aliases": ("lettuces",),
        "default_method": "direct",
        "days": {"direct": 45, "transplant": 35},
        "ranges": {"direct": (30, 55), "transplant": (25, 40)},
        "water_every_days": 1,
        "fertilize_every_days": 14,
        "note": "Leaf types are faster; head lettuce takes longer.",
    },
    "tomato": {
        "label": "Tomato",
        "aliases": ("tomatoes", "kamatis", "cherry tomato", "cherry tomatoes"),
        "default_method": "transplant",
        "days": {"direct": 100, "transplant": 75},
        "ranges": {"direct": (90, 120), "transplant": (65, 85)},
        "water_every_days": 2,
        "fertilize_every_days": 14,
        "note": "Large-fruited and processing varieties can take longer.",
    },
    "carrot": {
        "label": "Carrot",
        "aliases": ("carrots",),
        "default_method": "direct",
        "days": {"direct": 70, "transplant": 55},
        "ranges": {"direct": (65, 80), "transplant": (50, 65)},
        "water_every_days": 2,
        "fertilize_every_days": 21,
        "note": "Baby carrots can be pulled earlier; storage types take longer.",
    },
    "cabbage": {
        "label": "Cabbage",
        "aliases": ("cabbages", "repolyo"),
        "default_method": "transplant",
        "days": {"direct": 100, "transplant": 80},
        "ranges": {"direct": (90, 120), "transplant": (70, 90)},
        "water_every_days": 2,
        "fertilize_every_days": 14,
        "note": "Early varieties mature sooner than late storage types.",
    },
    "eggplant": {
        "label": "Eggplant",
        "aliases": ("eggplants", "talong", "aubergine"),
        "default_method": "transplant",
        "days": {"direct": 110, "transplant": 75},
        "ranges": {"direct": (100, 120), "transplant": (65, 85)},
        "water_every_days": 2,
        "fertilize_every_days": 14,
        "note": "Harvest while the skin is glossy and the fruit is young.",
    },
    "pepper": {
        "label": "Pepper",
        "aliases": (
            "peppers", "sili", "chili", "chilli", "chile", "capsicum",
            "bell pepper", "bell peppers", "hot pepper", "hot peppers",
            "chili pepper", "chile pepper", "siling labuyo", "siling haba",
        ),
        "default_method": "transplant",
        "days": {"direct": 105, "transplant": 75},
        "ranges": {"direct": (95, 120), "transplant": (65, 85)},
        "water_every_days": 2,
        "fertilize_every_days": 14,
        "note": "Sweet and hot varieties differ; color change adds time.",
    },
    "cucumber": {
        "label": "Cucumber",
        "aliases": ("cucumbers", "pipino"),
        "default_method": "direct",
        "days": {"direct": 55, "transplant": 50},
        "ranges": {"direct": (50, 65), "transplant": (45, 60)},
        "water_every_days": 1,
        "fertilize_every_days": 14,
        "note": "Pick regularly; overripe fruit slows production.",
    },
    "okra": {
        "label": "Okra",
        "aliases": ("okras", "lady finger", "ladyfinger"),
        "default_method": "direct",
        "days": {"direct": 55, "transplant": 50},
        "ranges": {"direct": (50, 60), "transplant": (45, 55)},
        "water_every_days": 2,
        "fertilize_every_days": 21,
        "note": "Harvest pods young, every 2-3 days.",
    },
    "beans": {
        "label": "Beans",
        "aliases": (
            "bean", "bush bean", "bush beans", "green bean", "green beans",
            "snap bean", "snap beans",
        ),
        "default_method": "direct",
        "days": {"direct": 55, "transplant": 50},
        "ranges": {"direct": (50, 60), "transplant": (45, 55)},
        "water_every_days": 2,
        "fertilize_every_days": 21,
        "note": "These are bush-bean timings; pole/sitaw beans take longer.",
    },
    "pechay": {
        "label": "Pechay",
        "aliases": (
            "pak choi", "pak choy", "bok choy", "bokchoi",
            "chinese cabbage", "chinese cabbages",
        ),
        "default_method": "direct",
        "days": {"direct": 35, "transplant": 30},
        "ranges": {"direct": (30, 40), "transplant": (25, 35)},
        "water_every_days": 1,
        "fertilize_every_days": 14,
        "note": "Harvest while leaves are young and tender.",
    },
    "kangkong": {
        "label": "Kangkong",
        "aliases": (
            "water spinach", "water spinaches", "swamp cabbage", "morning glory",
        ),
        "default_method": "direct",
        "days": {"direct": 30, "transplant": 25},
        "ranges": {"direct": (25, 35), "transplant": (20, 30)},
        "water_every_days": 1,
        "fertilize_every_days": 14,
        "note": "Can be harvested repeatedly by cutting tender tips.",
    },
    "mustasa": {
        "label": "Mustasa",
        "aliases": ("mustard greens", "mustard green", "mustard"),
        "default_method": "direct",
        "days": {"direct": 40, "transplant": 35},
        "ranges": {"direct": (30, 45), "transplant": (30, 40)},
        "water_every_days": 1,
        "fertilize_every_days": 14,
        "note": "Harvest leaves young; hot weather can make them pungent.",
    },
    "radish": {
        "label": "Radish",
        "aliases": ("radishes", "labanos"),
        "default_method": "direct",
        "days": {"direct": 30, "transplant": 25},
        "ranges": {"direct": (25, 35), "transplant": (20, 30)},
        "water_every_days": 1,
        "fertilize_every_days": 14,
        "note": "Do not leave roots in the ground too long; they become woody.",
    },
    "spinach": {
        "label": "Spinach",
        "aliases": ("spinaches",),
        "default_method": "direct",
        "days": {"direct": 45, "transplant": 40},
        "ranges": {"direct": (40, 50), "transplant": (35, 45)},
        "water_every_days": 1,
        "fertilize_every_days": 14,
        "note": "Harvest outer leaves or cut the whole rosette.",
    },
    "kale": {
        "label": "Kale",
        "aliases": ("kales",),
        "default_method": "direct",
        "days": {"direct": 60, "transplant": 50},
        "ranges": {"direct": (55, 70), "transplant": (45, 60)},
        "water_every_days": 1,
        "fertilize_every_days": 14,
        "note": "Can be harvested leaf by leaf over several weeks.",
    },
    "broccoli": {
        "label": "Broccoli",
        "aliases": ("broccolis",),
        "default_method": "transplant",
        "days": {"direct": 100, "transplant": 75},
        "ranges": {"direct": (90, 110), "transplant": (65, 85)},
        "water_every_days": 2,
        "fertilize_every_days": 14,
        "note": "Harvest the head before yellow flowers open.",
    },
    "cauliflower": {
        "label": "Cauliflower",
        "aliases": ("cauliflowers",),
        "default_method": "transplant",
        "days": {"direct": 100, "transplant": 75},
        "ranges": {"direct": (90, 110), "transplant": (65, 85)},
        "water_every_days": 2,
        "fertilize_every_days": 14,
        "note": "Heads can sunburn; tie outer leaves over them if needed.",
    },
    "ampalaya": {
        "label": "Ampalaya",
        "aliases": ("bitter gourd", "bitter melon", "bitter gourds"),
        "default_method": "transplant",
        "days": {"direct": 80, "transplant": 70},
        "ranges": {"direct": (70, 90), "transplant": (60, 80)},
        "water_every_days": 2,
        "fertilize_every_days": 14,
        "note": "Harvest young green fruits; growth needs a trellis.",
    },
    "sitaw": {
        "label": "Sitaw / pole beans",
        "aliases": (
            "sitao", "pole sitao", "pole beans", "pole bean", "string beans",
            "string bean",
        ),
        "default_method": "direct",
        "days": {"direct": 65, "transplant": 60},
        "ranges": {"direct": (60, 70), "transplant": (55, 65)},
        "water_every_days": 2,
        "fertilize_every_days": 21,
        "note": "Pole types need support and produce over a longer season.",
    },
    "kalabasa": {
        "label": "Kalabasa / squash",
        "aliases": ("squash", "squashes", "pumpkin", "pumpkins"),
        "default_method": "direct",
        "days": {"direct": 90, "transplant": 80},
        "ranges": {"direct": (80, 100), "transplant": (70, 90)},
        "water_every_days": 2,
        "fertilize_every_days": 21,
        "note": "Harvest when the rind is hard and the stem starts to cork.",
    },
    "corn": {
        "label": "Corn",
        "aliases": ("corns", "maize", "mais", "sweet corn"),
        "default_method": "direct",
        "days": {"direct": 80, "transplant": 70},
        "ranges": {"direct": (70, 90), "transplant": (65, 80)},
        "water_every_days": 2,
        "fertilize_every_days": 14,
        "note": "Harvest when silks have dried and kernels are milky.",
    },

    # Perennial fruit crops. For these, "direct" means seed-grown in place;
    # "transplant" means a grafted, marcotted, or nursery-raised planting
    # material. Tree crops take years, not weeks, so the values below are
    # expressed in days and the UI converts them to years.
    "rambutan": {
        "label": "Rambutan",
        "aliases": (
            "rambutans", "rambotan", "rambotans", "rambutan tree",
            "hairy lychee",
        ),
        "default_method": "transplant",
        "days": {"direct": 2190, "transplant": 1095},
        "ranges": {"direct": (1825, 2555), "transplant": (730, 1460)},
        "water_every_days": 3,
        "fertilize_every_days": 30,
        "note": "Seedlings bear in 5-7 years; grafted trees in 2-4. Needs wind protection and steady moisture.",
    },
    "mango": {
        "label": "Mango",
        "aliases": (
            "mangos", "mangoes", "mangga", "carabao mango", "piko mango",
            "mango tree",
        ),
        "default_method": "transplant",
        "days": {"direct": 2555, "transplant": 1095},
        "ranges": {"direct": (1825, 2920), "transplant": (730, 1460)},
        "water_every_days": 7,
        "fertilize_every_days": 30,
        "note": "Grafted trees usually bear in 2-4 years; seedlings take 5-8. A dry spell helps flowering.",
    },
    "calamansi": {
        "label": "Calamansi",
        "aliases": (
            "calamansis", "kalamansi", "kalamansis", "calamondin",
            "calamondins", "limonsito", "calamansi tree",
        ),
        "default_method": "transplant",
        "days": {"direct": 1460, "transplant": 548},
        "ranges": {"direct": (1095, 1825), "transplant": (365, 730)},
        "water_every_days": 3,
        "fertilize_every_days": 30,
        "note": "Grafted or marcotted trees can bear in 1-2 years; seedlings take 3-5.",
    },
    "papaya": {
        "label": "Papaya",
        "aliases": (
            "papayas", "kapayas", "papaw", "papaws", "papaya tree",
        ),
        "default_method": "transplant",
        "days": {"direct": 300, "transplant": 240},
        "ranges": {"direct": (270, 330), "transplant": (210, 300)},
        "water_every_days": 2,
        "fertilize_every_days": 30,
        "note": "Short-lived perennial; first fruit often in 8-10 months. Direct-seeded counts from sowing.",
    },
    "banana": {
        "label": "Banana",
        "aliases": (
            "bananas", "saging", "saba", "lakatan", "latundan", "tundan",
            "cardava", "cardaba", "banana plant",
        ),
        "default_method": "transplant",
        "days": {"direct": 450, "transplant": 300},
        "ranges": {"direct": (365, 540), "transplant": (270, 365)},
        "water_every_days": 2,
        "fertilize_every_days": 30,
        "note": (
            "Normally planted from suckers or tissue-culture plantlets; "
            "'transplant' is the normal method. First bunch in 9-12 months."
        ),
    },
    "jackfruit": {
        "label": "Jackfruit",
        "aliases": ("jackfruits", "langka", "nangka", "jakfruit"),
        "default_method": "transplant",
        "days": {"direct": 2555, "transplant": 1460},
        "ranges": {"direct": (1825, 2920), "transplant": (1095, 1825)},
        "water_every_days": 7,
        "fertilize_every_days": 30,
        "note": "Grafted trees bear in 3-5 years; seedlings take 5-8. Needs room for a large canopy.",
    },
    "avocado": {
        "label": "Avocado",
        "aliases": ("avocados", "abokado", "abocado", "avocado tree"),
        "default_method": "transplant",
        "days": {"direct": 2555, "transplant": 1460},
        "ranges": {"direct": (1825, 2555), "transplant": (1095, 1825)},
        "water_every_days": 7,
        "fertilize_every_days": 30,
        "note": "Grafted trees usually bear in 3-5 years; seedlings take 5-7. Needs well-drained soil.",
    },
    "lanzones": {
        "label": "Lanzones",
        "aliases": (
            "lanzone", "lansones", "lansone", "lanzon", "lanzones tree",
        ),
        "default_method": "transplant",
        "days": {"direct": 2920, "transplant": 1825},
        "ranges": {"direct": (2555, 3650), "transplant": (1460, 2190)},
        "water_every_days": 7,
        "fertilize_every_days": 30,
        "note": "Grafted trees bear in 4-6 years; seedlings take 7-10. Slow-growing and drought-sensitive.",
    },
    "durian": {
        "label": "Durian",
        "aliases": ("durians", "duryan", "durian tree"),
        "default_method": "transplant",
        "days": {"direct": 3285, "transplant": 1825},
        "ranges": {"direct": (2920, 3650), "transplant": (1460, 2190)},
        "water_every_days": 7,
        "fertilize_every_days": 30,
        "note": "Grafted trees bear in 4-6 years; seedlings take 8-10. Needs deep, well-drained soil.",
    },
}

DEFAULT_PROFILE = {
    "label": "Unknown crop",
    "aliases": (),
    "default_method": "direct",
    "days": {"direct": 60, "transplant": 50},
    "ranges": {"direct": (50, 70), "transplant": (45, 60)},
    "water_every_days": 2,
    "fertilize_every_days": 14,
    "note": "No crop-specific maturity data; adjust the estimate for your variety.",
}


def normalize_crop_name(name: str) -> str:
    """Lowercase a crop name and collapse punctuation/extra spaces."""
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def _build_alias_index() -> dict[str, str]:
    index = {}
    for key, profile in CROP_CATALOG.items():
        for alias in (key, *profile["aliases"]):
            index[normalize_crop_name(alias)] = key
    return index


ALIAS_INDEX = _build_alias_index()


def resolve_crop(name: str) -> tuple[str | None, dict, bool]:
    """Return (canonical key, profile, known) for a user-entered crop name."""
    key = ALIAS_INDEX.get(normalize_crop_name(name))
    if key:
        return key, CROP_CATALOG[key], True
    return None, DEFAULT_PROFILE, False


def defaults_for(name: str, start_method: str | None = None) -> dict:
    """Return crop-aware harvest and care defaults.

    ``start_method`` may be ``"direct"`` or ``"transplant"``. When omitted or
    invalid, the crop's recommended method is used.
    """
    key, profile, known = resolve_crop(name)
    method = start_method if start_method in START_METHODS else profile["default_method"]
    if method not in profile["days"]:
        method = profile["default_method"]

    days_min, days_max = profile["ranges"][method]
    return {
        "days_to_harvest": profile["days"][method],
        "days_min": days_min,
        "days_max": days_max,
        "start_method": method,
        "start_method_label": START_METHOD_LABELS[method],
        "crop_key": key or normalize_crop_name(name),
        "crop_label": profile["label"] if known else (name or "Unknown crop").strip(),
        "known": known,
        "note": profile["note"],
        "water_every_days": profile["water_every_days"],
        "fertilize_every_days": profile["fertilize_every_days"],
    }


def crop_guide_payload() -> dict:
    """JSON-safe crop data used by the Add/Edit Plant form."""
    return {
        "aliases": ALIAS_INDEX,
        "crops": {
            key: {
                "label": profile["label"],
                "default_method": profile["default_method"],
                "days": profile["days"],
                "ranges": {
                    method: [bounds[0], bounds[1]]
                    for method, bounds in profile["ranges"].items()
                },
                "note": profile["note"],
                "water_every_days": profile["water_every_days"],
                "fertilize_every_days": profile["fertilize_every_days"],
            }
            for key, profile in CROP_CATALOG.items()
        },
    }
