from __future__ import annotations

import os
import json
import smtplib
import ssl
from urllib.parse import urlsplit
from email.message import EmailMessage
from datetime import datetime

from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect, url_for, session, current_app
)
from flask_babel import Babel, _, get_locale
from flask_wtf import FlaskForm, CSRFProtect
from flask_wtf.csrf import generate_csrf, CSRFError
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, Regexp
from werkzeug.exceptions import TooManyRequests
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from calculator import SERVICES, ITEMS, HOURLY_RATES, CalculatorError, validate as validate_calculator, estimate, email_summary


load_dotenv()  # подхватит .env из корня проекта


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    # ── Конфигурация (prod/dev из config.py)
    if os.getenv("RENDER") == "true" or os.getenv("FLASK_ENV") == "production":
        from config import ProdConfig as AppConfig
    else:
        from config import DevConfig as AppConfig
    app.config.from_object(AppConfig)
    app.json.ensure_ascii = False
    if not app.debug and app.config["SECRET_KEY"] in (None, "", "dev-key", "change-me"):
        raise RuntimeError("Set a private SECRET_KEY environment variable in production")

    # Запасные значения (если забыли в config.py)
    app.config.setdefault("BABEL_DEFAULT_LOCALE", "de")
    app.config.setdefault("BABEL_TRANSLATION_DIRECTORIES", "translations")

    # ── Proxy (nginx), rate limit, CSRF
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
    limiter = Limiter(get_remote_address, app=app, default_limits=["200 per hour"])
    CSRFProtect(app)

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        if request.endpoint in ("contact", "calculate"):
            return {"ok": False, "errors": {"csrf_token": ["Please reload the page and try again."]}}, 400
        return error.get_response()

    @app.errorhandler(TooManyRequests)
    def rate_limit_error(error):
        if request.endpoint in ("contact", "calculate"):
            response = app.json.response({"ok": False, "errors": {"rate_limit": ["Too many requests. Please try again later."]}})
            response.status_code = 429
            return response
        return error.get_response()

    # ── Выбор языка
    def select_locale():
        lang = request.args.get("lang")
        if lang in app.config["LANGUAGES"]:
            session["lang"] = lang
            return lang
        if session.get("lang") in app.config["LANGUAGES"]:
            return session["lang"]
        # Первый визит всегда открывается на немецком независимо от языка браузера.
        return app.config.get("BABEL_DEFAULT_LOCALE", "de")

    Babel(app, locale_selector=select_locale)

    # ── Глобалы в шаблонах
    @app.context_processor
    def inject_globals():
        def locale_code():
            try:
                return str(get_locale()) or "de"
            except Exception:
                return "de"

        return {
            "csrf_token": generate_csrf,
            "now": datetime.utcnow,
            "get_locale": locale_code,
        }

    # ── Безопасные заголовки (CSP и пр.)
    @app.after_request
    def set_security_headers(resp):
        csp = (
            "default-src 'self'; "
            "img-src 'self' data: https://tile.openstreetmap.org "
            "https://www.google-analytics.com https://www.googletagmanager.com; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline' https://www.googletagmanager.com; "
            "connect-src 'self' "
            "https://*.google-analytics.com "
            "https://*.analytics.google.com "
            "https://www.googletagmanager.com; "
            "font-src 'self' data:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        resp.headers.setdefault("Content-Security-Policy", csp)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        return resp

    # ── Форма контакта
    class ContactForm(FlaskForm):
        name = StringField("name", validators=[DataRequired(), Length(max=80)])
        phone = StringField("phone", validators=[DataRequired(), Length(max=32), Regexp(r"(?=.*\d)[\d+\s()-]+\Z")])
        email = StringField("email", filters=[lambda value: value.strip() if value else value], validators=[Optional(), Email(), Length(max=120)])
        message = TextAreaField("message", validators=[Length(max=2000)])
        calculator_data = StringField("calculator_data", validators=[Optional(), Length(max=6000)])
        submit = SubmitField("send")

    # ── Отправка письма через SMTP (Gmail/App Password или другой провайдер)
    def send_email_smtp(name: str, phone: str, email: str | None, message: str | None) -> None:
        rcpt = os.getenv("MAIL_TO") or app.config.get("MAIL_TO")
        if not rcpt:
            raise RuntimeError("MAIL_TO is not set")

        subject_name = " ".join(name.splitlines())
        subject = f"Neue Anfrage: Transport & Umzugshilfe Alex — {subject_name}"
        body = (
            f"Name: {name}\n"
            f"Telefon: {phone}\n"
            f"E-mail: {email or '-'}\n\n"
            f"Nachricht:\n{message or '-'}\n"
        )

        msg = EmailMessage()
        msg["From"] = os.getenv("SMTP_USER", "no-reply@localhost")
        msg["To"] = rcpt
        msg["Subject"] = subject
        if email:
            msg["Reply-To"] = email
        msg.set_content(body)

        host = os.getenv("SMTP_HOST")
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER")
        pwd = os.getenv("SMTP_PASS")

        if not host:
            raise RuntimeError("SMTP_HOST is not set")

        tls_context = ssl.create_default_context()
        smtp_options = {"timeout": 20}
        if port == 465:
            smtp_options["context"] = tls_context
        smtp_class = smtplib.SMTP_SSL if port == 465 else smtplib.SMTP
        with smtp_class(host, port, **smtp_options) as s:
            s.ehlo()
            if port in (587, 25):
                s.starttls(context=tls_context)
                s.ehlo()
            if user and pwd:
                s.login(user, pwd)
            refused = s.send_message(msg)
            if refused:
                raise smtplib.SMTPRecipientsRefused(refused)

    # ── Роуты
    @app.route("/")
    @limiter.limit("30 per minute")
    def index():
        year = datetime.now().year
        return render_template("index.html", year=year, calculator_services=SERVICES,
                               calculator_items=ITEMS, calculator_rates=HOURLY_RATES)

    @app.post("/calculate")
    @limiter.limit("30 per minute")
    def calculate():
        if request.content_length and request.content_length > 12000:
            return {"ok": False, "errors": {"calculator": ["Request too large"]}}, 413
        try:
            data = validate_calculator(request.get_json(silent=True))
        except CalculatorError as error:
            return {"ok": False, "errors": {error.field: ["Please check this field"]}}, 400
        return {"ok": True, "estimate": estimate(data)}

    @app.route("/impressum")
    def impressum():
        return render_template("impressum.html")

    @app.route("/privacy")
    def privacy():
        return render_template("privacy.html")

    @app.route("/set-lang/<lang>")
    def set_lang(lang: str):
        if lang in app.config["LANGUAGES"]:
            session["lang"] = lang
        target = url_for("index")
        if request.referrer:
            referrer = urlsplit(request.referrer)
            origin = urlsplit(request.host_url)
            if (referrer.scheme, referrer.netloc) == (origin.scheme, origin.netloc):
                path = referrer.path
                if path.startswith("/") and not path.startswith("//") and "\\" not in path:
                    target = path
        return redirect(target)

    # ⚠️ ЕДИНСТВЕННЫЙ обработчик формы (старый дубликат удалён)
    @app.route("/contact", methods=["POST"])
    @limiter.limit("5/minute; 50/day")
    def contact():
        form = ContactForm()
        if form.validate_on_submit():
            message = form.message.data.strip() if form.message.data else ""
            if form.calculator_data.data:
                try:
                    calculation = validate_calculator(json.loads(form.calculator_data.data))
                except (ValueError, TypeError):
                    return {"ok": False, "errors": {"calculator_data": ["Please recalculate your move"]}}, 400
                message += "\n\n" + email_summary(calculation)
            try:
                send_email_smtp(
                    name=form.name.data.strip(),
                    phone=form.phone.data.strip(),
                    email=form.email.data.strip() if form.email.data else None,
                    message=message or None,
                )
            except Exception as e:
                current_app.logger.exception("Email send failed: %s", e)
                return {"ok": False, "errors": {"server": ["Mail delivery error"]}}, 500
            return {"ok": True}, 200
        return {"ok": False, "errors": form.errors}, 400

    return app


if __name__ == "__main__":
    app = create_app()
    app.run()
