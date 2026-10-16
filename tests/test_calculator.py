import json
import os
import re
import unittest
from unittest.mock import patch

from app import create_app
from calculator import CalculatorError, email_summary, estimate, validate


def example(**changes):
    data = {
        "distance": 25, "rooms": 2, "area": 50, "occupancy": "medium",
        "from_floor": 0, "to_floor": 0, "from_lift": "no", "to_lift": "no",
        "from_parking": "10", "to_parking": "10", "service": "one",
        "inventory_mode": "apartment", "items": {}, "other_items": "",
        "from_place": "Bremen", "to_place": "Bremen-Nord",
    }
    data.update(changes)
    return data


class CalculatorModelTests(unittest.TestCase):
    def quote(self, **changes):
        return estimate(validate(example(**changes)))

    def test_uses_site_rates_and_orders_range(self):
        result = self.quote()
        self.assertGreater(result["price_low"], 0)
        self.assertGreater(result["price_high"], result["price_low"])
        self.assertEqual(result["price_low"], result["hours_low"] * 60)
        two = self.quote(service="two")
        self.assertEqual(two["price_low"], two["hours_low"] * 80)
        self.assertEqual(two["price_high"], two["hours_high"] * 100)

    def test_driver_only_never_invents_a_price(self):
        result = self.quote(service="driver")
        self.assertIsNone(result["price_low"])
        self.assertIsNone(result["hours_low"])

    def test_inventory_adds_25_percent_to_both_prices_only(self):
        # 200 boxes = 16 m³, the same volume as the default apartment.
        for service in ("one", "two"):
            with self.subTest(service=service):
                apartment = self.quote(service=service)
                inventory = self.quote(service=service, inventory_mode="items", items={"boxes": 200})
                for key in ("price_low", "price_high"):
                    self.assertEqual(inventory[key], apartment[key] * 1.25)
                for key in ("hours_low", "hours_high", "volume_m3", "trips", "route_km"):
                    self.assertEqual(inventory[key], apartment[key])
        self.assertEqual(self.quote(inventory_mode="items", items={"boxes": 200})["price_high"], 562.5)

    def test_apartment_ignores_leftover_inventory_and_notes_for_markup(self):
        result = self.quote(items={"boxes": 200}, other_items="Additional furniture")
        self.assertEqual((result["price_low"], result["price_high"]), (300, 450))

    def test_inventory_driver_price_stays_on_request(self):
        result = self.quote(service="driver", inventory_mode="items", items={"boxes": 200})
        self.assertIsNone(result["price_low"])
        self.assertIsNone(result["price_high"])

    def test_distance_increases_estimate(self):
        self.assertGreater(self.quote(distance=300)["price_low"], self.quote(distance=5)["price_low"])

    def test_room_area_and_occupancy_affect_volume(self):
        self.assertGreater(self.quote(area=100)["volume_m3"], self.quote(area=50)["volume_m3"])
        self.assertGreater(self.quote(rooms=5)["volume_m3"], self.quote(rooms=2)["volume_m3"])
        self.assertGreater(self.quote(occupancy="high")["volume_m3"], self.quote(occupancy="low")["volume_m3"])

    def test_both_floors_lifts_and_parking_affect_duration(self):
        baseline = self.quote()["hours_high"]
        for end in ("from", "to"):
            stairs = self.quote(**{end + "_floor": 5})["hours_high"]
            lift = self.quote(**{end + "_floor": 5, end + "_lift": "yes"})["hours_high"]
            self.assertGreater(stairs, baseline)
            self.assertLess(lift, stairs)
            self.assertGreater(self.quote(area=100, **{end + "_parking": "30"})["hours_high"], self.quote(area=100)["hours_high"])

    def test_inventory_replaces_area_instead_of_double_counting(self):
        one = self.quote(inventory_mode="items", items={"boxes": 10, "sofa": 1}, area=20)
        two = self.quote(inventory_mode="items", items={"boxes": 10, "sofa": 1}, area=200)
        self.assertEqual(one, two)
        self.assertEqual(one["volume_m3"], 2.8)
        self.assertEqual(one["trips"], 1)

    def test_extra_trips_include_return_legs(self):
        result = self.quote(inventory_mode="items", items={"sofa": 15}, distance=10)
        self.assertEqual(result["trips"], 3)
        self.assertEqual(result["route_km"], 50)

    def test_free_text_and_long_walk_are_flagged_for_review(self):
        self.assertTrue(self.quote(other_items="Piano")["manual_review"])
        self.assertTrue(self.quote(to_parking="30")["manual_review"])

    def test_invalid_numbers_and_choices_are_rejected(self):
        changes = [
            {"distance": -1}, {"distance": float("nan")}, {"distance": float("inf")},
            {"distance": True}, {"distance": 3001}, {"rooms": 1.5}, {"area": 0},
            {"service": "free"}, {"occupancy": []}, {"from_floor": 21},
            {"to_lift": True}, {"from_parking": "500"}, {"other_items": "a" * 501},
            {"items": {"boxes": -1}}, {"items": {"sofa": 1.5}}, {"items": {"sofa": True}},
            {"items": {"boxes": 301}}, {"inventory_mode": "items", "items": {}},
        ]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(CalculatorError):
                validate(example(**change))

    def test_summary_recomputes_client_supplied_price(self):
        data = validate(example(price_low=1, price_high=1))
        summary = email_summary(data)
        self.assertIn("60", str(estimate(data)["hourly_low"]))
        self.assertIn("UMZUGSRECHNER", summary)
        self.assertNotIn("Orientierung: 1–1 EUR", summary)


class CalculatorEndpointTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"RENDER": "false", "FLASK_ENV": "development"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.app = create_app()
        self.app.config.update(TESTING=True, SECRET_KEY="test-key")
        self.client = self.app.test_client()
        html = self.client.get("/").text
        self.token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)

    def calculate(self, data):
        return self.client.post("/calculate", json=data, headers={"X-CSRFToken": self.token})

    def test_valid_request_and_csrf(self):
        response = self.calculate(example())
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.json["estimate"]["price_low"], 0)
        response = self.client.post("/calculate", json=example())
        self.assertEqual(response.status_code, 400)
        self.assertIn("csrf_token", response.json["errors"])

    def test_appliances_are_translated_and_included_in_quote_and_email(self):
        items = {"tv": 1, "stove": 1, "dishwasher": 1, "dryer": 1,
                 "freezer": 1, "oven": 1, "microwave": 1, "vacuum": 1}
        for lang, label in (("de", "Geschirrspüler"), ("en", "Dishwasher"), ("ru", "Посудомоечная машина")):
            html = self.client.get("/", query_string={"lang": lang}).text
            self.assertIn(label, html)
            for key in items:
                self.assertIn(f'id="calc-item-{key}"', html)
        calculation = example(inventory_mode="items", items=items)
        response = self.calculate(calculation)
        self.assertEqual(response.status_code, 200)
        result = response.json["estimate"]
        self.assertEqual(result["volume_m3"], 2.95)
        self.assertEqual(result["price_low"], result["hours_low"] * 60 * 1.25)
        self.assertEqual(result["price_high"], result["hours_high"] * 60 * 1.25)
        summary = email_summary(validate(calculation))
        self.assertIn("Geschirrspüler: 1", summary)
        self.assertIn("Fernseher: 1", summary)
        self.assertIn("Herd mit Backofen: 1", summary)

    def test_invalid_json_and_input(self):
        for data in ([], None, {}, example(distance=-10)):
            with self.subTest(data=data):
                self.assertEqual(self.calculate(data).status_code, 400)

    def test_rate_limit(self):
        for _ in range(30):
            self.assertEqual(self.calculate(example()).status_code, 200)
        response = self.calculate(example())
        self.assertEqual(response.status_code, 429)
        self.assertIn("rate_limit", response.json["errors"])

    def test_contact_includes_server_generated_calculation(self):
        data = {"name": "Test", "phone": "12345", "email": "", "message": "My original message",
                "csrf_token": self.token, "calculator_data": json.dumps(example(price_low=1))}
        with patch.dict(os.environ, {"MAIL_TO": "owner@example.com", "SMTP_HOST": "smtp.example.com", "SMTP_PORT": "587"}), patch("app.smtplib.SMTP") as smtp:
            connection = smtp.return_value.__enter__.return_value
            connection.send_message.return_value = {}
            self.assertEqual(self.client.post("/contact", data=data).status_code, 200)
            body = connection.send_message.call_args.args[0].get_content()
            self.assertIn("My original message", body)
            self.assertIn("UMZUGSRECHNER", body)
            self.assertIn("Entfernung A-B: 25 km", body)
            self.assertIn("Keine Festpreis-Zusage", body)

    def test_contact_rejects_malformed_calculation_without_sending(self):
        with patch("app.smtplib.SMTP") as smtp:
            response = self.client.post("/contact", data={"name": "Test", "phone": "12345", "csrf_token": self.token, "calculator_data": '{"distance": -1}'})
            self.assertEqual(response.status_code, 400)
            self.assertIn("calculator_data", response.json["errors"])
            smtp.assert_not_called()

    def test_inventory_api_and_email_include_markup_once(self):
        calculation = example(inventory_mode="items", items={"boxes": 200})
        result = self.calculate(calculation).json["estimate"]
        self.assertEqual((result["price_low"], result["price_high"]), (375, 562.5))
        data = {"name": "Test", "phone": "12345", "csrf_token": self.token,
                "calculator_data": json.dumps(calculation)}
        with patch.dict(os.environ, {"MAIL_TO": "owner@example.com", "SMTP_HOST": "smtp.example.com", "SMTP_PORT": "587"}), patch("app.smtplib.SMTP") as smtp:
            connection = smtp.return_value.__enter__.return_value
            connection.send_message.return_value = {}
            self.assertEqual(self.client.post("/contact", data=data).status_code, 200)
            body = connection.send_message.call_args.args[0].get_content()
            self.assertIn(f"Orientierung: {result['price_low']}–{result['price_high']} EUR", body)


if __name__ == "__main__":
    unittest.main()
