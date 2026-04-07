from __future__ import annotations
import os
from datetime import timedelta

class Config:
    # Ключ сессии/CSRF (в .env обязательно задаём свой)
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key")

    # Формы/CSRF
    WTF_CSRF_TIME_LIMIT = 60 * 60 * 8  # 8 часов

    # Сессии/куки
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = True       # на проде true

    PREFERRED_URL_SCHEME = "https"

    # Локализация (Flask-Babel)
    LANGUAGES = ["ru", "de", "en"]
    BABEL_DEFAULT_LOCALE = "de"                      # базовый язык строк
    BABEL_TRANSLATION_DIRECTORIES = "translations"   # папка с переводами
    BABEL_DEFAULT_TIMEZONE = "Europe/Berlin"         # опционально

    # Удобно при правке шаблонов
    TEMPLATES_AUTO_RELOAD = True
    JSON_AS_ASCII = False   # чтобы JSON не экранировал кириллицу

class ProdConfig(Config):
    ENV = "production"
    DEBUG = False

class DevConfig(Config):
    ENV = "development"
    DEBUG = True
    SESSION_COOKIE_SECURE = False      # локально без HTTPS
