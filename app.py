from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from datetime import datetime

from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect, url_for, session, make_response, current_app
)
from flask_babel import Babel, _, get_locale
from flask_wtf import FlaskForm, CSRFProtect
from flask_wtf.csrf import generate_csrf
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


load_dotenv()  # подхватит .env из корня проекта


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    # ── Конфигурация (prod/dev из config.py)
    if os.getenv("FLASK_ENV") == "production":
        from config import ProdConfig as AppConfig
    else:
        from config import DevConfig as AppConfig
    app.config.from_object(AppConfig)

    # Запасные значения (если забыли в config.py)
    app.config.setdefault("BABEL_DEFAULT_LOCALE", "ru")
    app.config.setdefault("BABEL_TRANSLATION_DIRECTORIES", "translations")

    # ── Proxy (nginx), rate limit, CSRF
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
    limiter = Limiter(get_remote_address, app=app, default_limits=["200 per hour"])
    CSRFProtect(app)

    # ── Выбор языка
    def select_locale():
        if "lang" in session and session["lang"] in app.config["LANGUAGES"]:
            return session["lang"]
        lang = request.args.get("lang")
        if lang in app.config["LANGUAGES"]:
            session["lang"] = lang
            return lang
        return request.accept_languages.best_match(app.config["LANGUAGES"]) or "ru"

    Babel(app, locale_selector=select_locale)

    # ── Глобалы в шаблонах
    @app.context_processor
    def inject_globals():
        def locale_code():
            try:
                return str(get_locale()) or "ru"
            except Exception:
                return "ru"

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
            "img-src 'self' data: https://tile.openstreetmap.org; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; "
            "connect-src 'self'; "
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
        phone = StringField("phone", validators=[DataRequired(), Length(max=32)])
        email = StringField("email", validators=[Email(), Length(max=120)])
        message = TextAreaField("message", validators=[Length(max=2000)])
        submit = SubmitField("send")

    # ── Отправка письма через SMTP (Gmail/App Password или другой провайдер)
    def send_email_smtp(name: str, phone: str, email: str | None, message: str | None) -> None:
        rcpt = os.getenv("MAIL_TO") or app.config.get("MAIL_TO")
        if not rcpt:
            current_app.logger.warning("MAIL_TO is not set; skipping email send")
            return

        subject = f"Neue Anfrage: Transport & Umzugshilfe Alex — {name}"
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
        msg.set_content(body)

        host = os.getenv("SMTP_HOST")
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER")
        pwd = os.getenv("SMTP_PASS")

        if not host:
            current_app.logger.warning("SMTP_HOST not set; skipping email send")
            return

        with smtplib.SMTP(host, port, timeout=20) as s:
            s.ehlo()
            if port in (587, 25):
                s.starttls()
            if user and pwd:
                s.login(user, pwd)
            s.send_message(msg)

    # ── Роуты
    @app.route("/")
    @limiter.limit("30 per minute")
    def index():
        year = datetime.now().year
        return render_template("index.html", year=year)

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
        return redirect(request.referrer or url_for("index"))

    # ⚠️ ЕДИНСТВЕННЫЙ обработчик формы (старый дубликат удалён)
    @app.route("/contact", methods=["POST"])
    @limiter.limit("5/minute; 50/day")
    def contact():
        form = ContactForm()
        if form.validate_on_submit():
            try:
                send_email_smtp(
                    name=form.name.data.strip(),
                    phone=form.phone.data.strip(),
                    email=form.email.data.strip() if form.email.data else None,
                    message=form.message.data.strip() if form.message.data else None,
                )
            except Exception as e:
                current_app.logger.exception("Email send failed: %s", e)
                return {"ok": False, "errors": {"server": ["Mail delivery error"]}}, 500
            return {"ok": True}, 200
        return {"ok": False, "errors": form.errors}, 400

    # (опционально) Быстрый тест отправки письма
    @app.get("/testmail")
    def testmail():
        try:
            send_email_smtp("Test", "+49 000000", None, "Hello from Flask")
            return "OK"
        except Exception as e:
            current_app.logger.exception("testmail error")
            return f"ERROR: {e}", 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
