"""Preliminary moving estimates. All modelling assumptions are kept here.

Hourly prices come from the existing website, not a confirmed full tariff.
Time/volume coefficients are planning estimates, NOT separate surcharges.
No mileage fee, depot travel, parking permits, packing or assembly is included.
Review these assumptions with the owner before treating results as quotations.
"""
from __future__ import annotations

import math


SERVICES = (
    ("driver", "Transporter mit Fahrer", "Sie übernehmen das Be- und Entladen."),
    ("one", "Sprinter + 1 Umzugshelfer", "Der Fahrer hilft beim Tragen und Laden."),
    ("two", "Sprinter + 2 Umzugshelfer", "Zwei Helfer packen an. Einer davon fährt."),
)
ITEMS = (
    ("boxes", "Umzugskartons", 0.08),
    ("sofa", "Sofa", 2.0),
    ("armchair", "Sessel", 0.8),
    ("bed", "Bett mit Matratze", 1.5),
    ("wardrobe", "Kleiderschrank", 2.0),
    ("dresser", "Kommode", 0.7),
    ("table", "Tisch", 0.8),
    ("chair", "Stuhl", 0.2),
    ("desk", "Schreibtisch", 0.8),
    ("shelf", "Regal", 0.6),
    ("washer", "Waschmaschine", 0.5),
    ("fridge", "Kühlschrank", 0.7),
)
HOURLY_RATES = {"driver": None, "one": (60, 60), "two": (80, 100)}
MODEL = {
    "occupancy": {"low": 0.22, "medium": 0.32, "high": 0.45},
    "van_volume_m3": 14,
    "average_speed_kmh": 50,
    "minutes_per_m3_per_stop": 5.5,
    "stairs_minutes_per_m3_per_floor": 1.3,
    "lift_minutes_per_m3": 1.0,
    "walk_minutes_per_m3_per_extra_10m": 0.6,
    "setup_hours_per_trip": 0.5,
    "two_person_productivity": 1.7,
    "inventory_price_multiplier": 1.25,
}


class CalculatorError(ValueError):
    def __init__(self, field: str):
        self.field = field
        super().__init__(field)


def validate(data: object) -> dict:
    """Validate untrusted browser input; never accept client-supplied totals."""
    if not isinstance(data, dict):
        raise CalculatorError("calculator")

    def number(key, low, high, integer=False):
        value = data.get(key)
        if isinstance(value, bool):
            raise CalculatorError(key)
        try:
            result = float(value)
        except (TypeError, ValueError, OverflowError):
            raise CalculatorError(key) from None
        if not math.isfinite(result) or not low <= result <= high or (integer and not result.is_integer()):
            raise CalculatorError(key)
        return int(result) if integer else result

    def choice(key, options):
        value = data.get(key)
        if value not in options:
            raise CalculatorError(key)
        return value

    def text(key, limit):
        value = data.get(key, "")
        if not isinstance(value, str) or len(value) > limit:
            raise CalculatorError(key)
        return value.strip()

    clean = {
        "from_place": text("from_place", 120),
        "to_place": text("to_place", 120),
        "distance": number("distance", 0, 3000),
        "rooms": number("rooms", 1, 15, True),
        "area": number("area", 10, 500),
        "occupancy": choice("occupancy", ("low", "medium", "high")),
        "service": choice("service", ("driver", "one", "two")),
        "inventory_mode": choice("inventory_mode", ("apartment", "items")),
        "other_items": text("other_items", 500),
    }
    for end in ("from", "to"):
        clean[f"{end}_floor"] = number(f"{end}_floor", 0, 20, True)
        clean[f"{end}_lift"] = choice(f"{end}_lift", ("yes", "no"))
        clean[f"{end}_parking"] = choice(f"{end}_parking", ("10", "20", "30"))
    inventory = data.get("items", {})
    if not isinstance(inventory, dict):
        raise CalculatorError("items")
    clean["items"] = {}
    for key, _, _ in ITEMS:
        value = inventory.get(key, 0)
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= (300 if key == "boxes" else 50):
            raise CalculatorError("items")
        clean["items"][key] = value
    if clean["inventory_mode"] == "items" and not any(clean["items"].values()):
        raise CalculatorError("items")
    return clean


def estimate(data: dict) -> dict:
    """Calculate a range from validated data using an explicitly rough model."""
    if data["inventory_mode"] == "items":
        volume = sum(data["items"][key] * size for key, _, size in ITEMS)
    else:
        coefficient = MODEL["occupancy"][data["occupancy"]]
        volume = max(data["area"], data["rooms"] * 15) * coefficient
    volume = round(volume, 2)
    trips = max(1, math.ceil(volume / MODEL["van_volume_m3"]))
    route_km = data["distance"] * (2 * trips - 1)
    result = {
        "volume_m3": volume, "trips": trips, "route_km": round(route_km, 1),
        "hours_low": None, "hours_high": None, "price_low": None, "price_high": None,
        "hourly_low": None, "hourly_high": None,
        "manual_review": bool(data["other_items"]) or any(data[f"{end}_parking"] == "30" for end in ("from", "to")),
    }
    rates = HOURLY_RATES[data["service"]]
    if rates is None:
        return result
    handling_minutes = 0.0
    for end in ("from", "to"):
        minutes = MODEL["minutes_per_m3_per_stop"]
        floor = data[f"{end}_floor"]
        if floor:
            minutes += MODEL["lift_minutes_per_m3"] if data[f"{end}_lift"] == "yes" else floor * MODEL["stairs_minutes_per_m3_per_floor"]
        minutes += (int(data[f"{end}_parking"]) - 10) / 10 * MODEL["walk_minutes_per_m3_per_extra_10m"]
        handling_minutes += volume * minutes
    productivity = MODEL["two_person_productivity"] if data["service"] == "two" else 1
    hours = handling_minutes / 60 / productivity + route_km / MODEL["average_speed_kmh"] + trips * MODEL["setup_hours_per_trip"]
    lower = max(0.5, math.ceil(hours * 0.85 * 2) / 2)
    upper = max(lower + 0.5, math.ceil((hours * 1.2 + 0.5) * 2) / 2)
    price_multiplier = MODEL["inventory_price_multiplier"] if data["inventory_mode"] == "items" else 1
    result.update(hours_low=lower, hours_high=upper,
                  price_low=round(lower * rates[0] * price_multiplier, 2),
                  price_high=round(upper * rates[1] * price_multiplier, 2),
                  hourly_low=rates[0], hourly_high=rates[1])
    return result


def email_summary(data: dict) -> str:
    """German summary for the business; amounts are recalculated server-side."""
    result = estimate(data)
    service = next(label for key, label, _ in SERVICES if key == data["service"])
    occupancy = {"low": "wenig", "medium": "mittel", "high": "viel"}[data["occupancy"]]
    lines = ["UMZUGSRECHNER — unverbindliche Orientierung",
             f"Von: {data['from_place'] or '-'}", f"Nach: {data['to_place'] or '-'}",
             f"Entfernung A-B: {data['distance']:g} km",
             f"Wohnung: {data['rooms']} Zimmer, {data['area']:g} m², Einrichtung: {occupancy}",
             f"Service: {service}"]
    for end, label in (("from", "Auszug"), ("to", "Einzug")):
        floor = data[f"{end}_floor"]
        parking = data[f"{end}_parking"] + ("+" if data[f"{end}_parking"] == "30" else "")
        lines.append(f"{label}: Etage {floor}, Aufzug: {data[f'{end}_lift']}, Trageweg: {parking} m")
    lines.append("Berechnungsbasis: " + ("Inventarliste" if data["inventory_mode"] == "items" else "Wohnungsgröße"))
    if data["inventory_mode"] == "items":
        lines.extend(f"  {label}: {data['items'][key]}" for key, label, _ in ITEMS if data["items"][key])
    if data["other_items"]:
        lines.append("Weitere Angaben (separat zu prüfen): " + data["other_items"])
    lines.append(f"Geschätztes Volumen: {result['volume_m3']:g} m³; Fahrten A-B: {result['trips']}")
    if result["price_low"] is not None:
        lines.append(f"Grobe Dauer: {result['hours_low']:g}–{result['hours_high']:g} Std.; Orientierung: {result['price_low']}–{result['price_high']} EUR")
    else:
        lines.append("Preis: auf Anfrage")
    lines.append("Keine Festpreis-Zusage. An-/Abfahrt zum Betrieb, Parkgebühren, Verpackung und Montage nicht enthalten.")
    return "\n".join(lines)
