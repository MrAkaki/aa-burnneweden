from .base import *

SECRET_KEY = os.environ.get("AA_SECRET_KEY", "testsite-insecure-secret-key-change-me")
SITE_NAME = os.environ.get("AA_SITENAME", "AA Testsite")
SITE_URL = os.environ.get("AA_SITE_URL", "http://localhost:8000")
CSRF_TRUSTED_ORIGINS = [SITE_URL]
DEBUG = True

DATABASES["default"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": "/home/allianceauth/myauth/db/aa.sqlite3",
}

ESI_SSO_CALLBACK_URL = f"{SITE_URL}/sso/callback"
ESI_SSO_CLIENT_ID = os.environ.get("ESI_SSO_CLIENT_ID", "")
ESI_SSO_CLIENT_SECRET = os.environ.get("ESI_SSO_CLIENT_SECRET", "")
ESI_USER_CONTACT_EMAIL = os.environ.get("ESI_USER_CONTACT_EMAIL", "")

REGISTRATION_VERIFY_EMAIL = False

ROOT_URLCONF = "myauth.urls"
WSGI_APPLICATION = "myauth.wsgi.application"
STATIC_ROOT = "/var/www/myauth/static/"
STATIC_URL = "/static/"

# Serve static files via gunicorn (no nginx needed for testsite)
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
BROKER_URL = f"redis://{os.environ.get('AA_REDIS', 'redis:6379')}/0"
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{os.environ.get('AA_REDIS', 'redis:6379')}/1",
    }
}

INSTALLED_APPS += [
    "aa_burnneweden",
    "allianceauth.services.modules.discord",
    "aadiscordbot",
]

# Ensure startup INFO logs from aa_burnneweden.app are visible in container logs.
LOGGING = globals().get("LOGGING", {}).copy()
LOGGING.setdefault("version", 1)
LOGGING.setdefault("disable_existing_loggers", False)

_logging_handlers = LOGGING.setdefault("handlers", {})
_logging_handlers.setdefault("console", {"class": "logging.StreamHandler"})

_logging_loggers = LOGGING.setdefault("loggers", {})
_logging_loggers["aa_burnneweden.app"] = {
    "handlers": ["console"],
    "level": "INFO",
    "propagate": False,
}

# Optional AA apps:
# for _app in [
#     "allianceauth.corputils",
#     "allianceauth.optimer",
#     "allianceauth.srp",
#     "allianceauth.timerboard",
# ]:
#     if _app not in INSTALLED_APPS:
#         INSTALLED_APPS.append(_app)

DISCORD_CALLBACK_URL = f"{SITE_URL}/discord/callback/"
DISCORD_GUILD_ID = os.environ.get("DISCORD_GUILD_ID", "")
DISCORD_APP_ID = os.environ.get("DISCORD_APP_ID", "")
DISCORD_APP_SECRET = os.environ.get("DISCORD_APP_SECRET", "")
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DISCORD_SYNC_NAMES = False

AUTHBOT_DISCORD_APP_ID = os.environ.get("AUTHBOT_DISCORD_APP_ID", DISCORD_APP_ID)
AUTHBOT_DISCORD_BOT_TOKEN = os.environ.get("AUTHBOT_DISCORD_BOT_TOKEN", DISCORD_BOT_TOKEN)

DISCORD_BOT_COGS = [
    "aadiscordbot.cogs.auth",
]

from celery.schedules import crontab

CELERYBEAT_SCHEDULE = globals().get("CELERYBEAT_SCHEDULE", {})
CELERYBEAT_SCHEDULE["aa-burnneweden-notify-pullers"] = {
    "task": "aa_burnneweden.notifications.notify_pullers_open_contracts",
    "schedule": crontab(minute="*/15"),
}
