import os
from pathlib import Path
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = os.environ.get("DJANGO_DEBUG") == "1"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",")
    if host.strip()
]

PAYMENT_PROVIDER = os.environ.get("PAYMENT_PROVIDER", "mock").strip()
if PAYMENT_PROVIDER not in {"mock", "yookassa"}:
    raise ImproperlyConfigured("PAYMENT_PROVIDER must be mock or yookassa.")

YOOKASSA_SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID", "").strip()
YOOKASSA_SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY", "").strip()
YOOKASSA_RETURN_BASE_URL = os.environ.get("YOOKASSA_RETURN_BASE_URL", "http://127.0.0.1:8000").strip()
if PAYMENT_PROVIDER == "yookassa":
    try:
        return_base = urlsplit(YOOKASSA_RETURN_BASE_URL)
        if (
            return_base.scheme not in {"http", "https"}
            or not return_base.hostname
            or return_base.port == 0
            or return_base.username is not None
            or return_base.path not in {"", "/"}
            or return_base.query
            or return_base.fragment
        ):
            raise ValueError
    except ValueError:
        raise ImproperlyConfigured("YOOKASSA_RETURN_BASE_URL must be an HTTP(S) origin.") from None

    YOOKASSA_RETURN_BASE_URL = f"{return_base.scheme}://{return_base.netloc}"
    CSRF_TRUSTED_ORIGINS = [YOOKASSA_RETURN_BASE_URL]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.postgres",
    "django.contrib.staticfiles",
    "accounts",
    "catalog",
    "cart",
    "orders",
    "payments",
    "delivery",
    "backoffice",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "dostavochking.urls"
WSGI_APPLICATION = "dostavochking.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "dostavochking"),
        "USER": os.environ.get("POSTGRES_USER", "dostavochking"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "OPTIONS": {"connect_timeout": 3},
    }
}

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "catalog:list"
LOGOUT_REDIRECT_URL = "catalog:list"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
