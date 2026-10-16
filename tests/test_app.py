import os
import re
import smtplib
import unittest
from unittest.mock import patch

from app import create_app


class ContactTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "RENDER": "true", "FLASK_ENV": "production",
            "MAIL_TO": "owner@example.com", "SMTP_HOST": "smtp.example.com",
            "SMTP_PORT": "587", "SMTP_USER": "sender@example.com",
            "SMTP_PASS": "test-password",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        with patch("config.ProdConfig.SECRET_KEY", "test-secret"):
            self.app = create_app()
        self.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = self.app.test_client()
        response = self.client.get("/", base_url="https://localhost")
        self.token = re.search(r'name="csrf_token" value="([^"]+)"', response.text).group(1)
        self.smtp_patch = patch("app.smtplib.SMTP")
        self.smtp = self.smtp_patch.start()
        self.addCleanup(self.smtp_patch.stop)
        self.connection = self.smtp.return_value.__enter__.return_value
        self.connection.send_message.return_value = {}

    def post(self, **values):
        data = {"name": "Test", "phone": "+49 123456", "email": "",
                "message": "Moving inquiry", "csrf_token": self.token}
        data.update(values)
        return self.client.post("/contact", data=data, base_url="https://localhost",
                                headers={"Referer": "https://localhost/"})

    def test_optional_email_and_existing_starttls(self):
        self.assertEqual(self.post().status_code, 200)
        self.smtp.assert_called_once_with("smtp.example.com", 587, timeout=20)
        self.connection.starttls.assert_called_once()
        self.connection.login.assert_called_once_with("sender@example.com", "test-password")
        message = self.connection.send_message.call_args.args[0]
        self.assertEqual(message["From"], "sender@example.com")
        self.assertEqual(message["To"], "owner@example.com")
        self.assertNotIn("Reply-To", message)

    def test_reply_to_and_invalid_email(self):
        self.assertEqual(self.post(email="invalid").status_code, 400)
        self.smtp.assert_not_called()
        self.assertEqual(self.post(email="client@example.com").status_code, 200)
        self.assertEqual(self.connection.send_message.call_args.args[0]["Reply-To"], "client@example.com")

    def test_missing_smtp_configuration_is_not_success(self):
        with patch.dict(os.environ, {"SMTP_HOST": ""}):
            response = self.post()
        self.assertEqual(response.status_code, 500)
        self.assertFalse(response.json["ok"])
        self.smtp.assert_not_called()

    def test_missing_recipient_is_not_success(self):
        with patch.dict(os.environ, {"MAIL_TO": ""}):
            self.assertEqual(self.post().status_code, 500)
        self.smtp.assert_not_called()

    def test_delivery_failure_is_not_success(self):
        self.connection.send_message.side_effect = smtplib.SMTPException("delivery failed")
        self.assertEqual(self.post().status_code, 500)

    def test_refused_recipient_is_not_success(self):
        self.connection.send_message.return_value = {"owner@example.com": (550, b"refused")}
        self.assertEqual(self.post().status_code, 500)

    def test_blank_name_and_invalid_phone(self):
        self.assertEqual(self.post(name="   ").status_code, 400)
        self.assertEqual(self.post(phone="letters").status_code, 400)
        self.smtp.assert_not_called()

    def test_ssl_port(self):
        with patch.dict(os.environ, {"SMTP_PORT": "465"}), patch("app.smtplib.SMTP_SSL") as smtp_ssl:
            connection = smtp_ssl.return_value.__enter__.return_value
            connection.send_message.return_value = {}
            self.assertEqual(self.post().status_code, 200)
            connection.starttls.assert_not_called()
            smtp_ssl.assert_called_once()
            self.smtp.assert_not_called()

    def test_csrf_and_rate_limit_return_json(self):
        response = self.post(csrf_token="invalid")
        self.assertEqual(response.status_code, 400)
        self.assertIn("csrf_token", response.json["errors"])
        for _ in range(6):
            response = self.post()
        self.assertEqual(response.status_code, 429)
        self.assertIn("rate_limit", response.json["errors"])

    def test_public_mail_test_is_removed(self):
        self.assertEqual(self.client.get("/testmail").status_code, 404)
        self.smtp.assert_not_called()

    def test_language_redirects_stay_local(self):
        for referrer in ("https://evil.example/", "https://localhost//evil.example/", "https://localhost/\\evil.example/"):
            response = self.client.get("/set-lang/en", base_url="https://localhost", headers={"Referer": referrer})
            self.assertEqual(response.headers["Location"], "/")
        response = self.client.get("/set-lang/ru", base_url="https://localhost", headers={"Referer": "https://localhost/privacy"})
        self.assertEqual(response.headers["Location"], "/privacy")
        response = self.client.get("/?lang=en", base_url="https://localhost")
        self.assertIn('<html lang="en">', response.text)

    def test_render_uses_secure_production_configuration(self):
        self.assertFalse(self.app.debug)
        self.assertTrue(self.app.config["SESSION_COOKIE_SECURE"])

    def test_production_rejects_placeholder_secret(self):
        with patch("config.ProdConfig.SECRET_KEY", "dev-key"):
            with self.assertRaises(RuntimeError):
                create_app()


if __name__ == "__main__":
    unittest.main()
