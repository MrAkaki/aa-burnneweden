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
    'aa_burnneweden',
    # Uncomment to enable optional AA apps:
    # 'allianceauth.corputils',
    # 'allianceauth.optimer',
    # 'allianceauth.srp',
    # 'allianceauth.timerboard',
]
