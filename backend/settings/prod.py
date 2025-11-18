# -*- coding: utf-8 -*-
"""
Created on June 15, 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
import datetime
from pathlib import Path

import sentry_sdk
from dotenv import dotenv_values

environ = dotenv_values(".env")

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
APPEND_SLASH = True

ALLOWED_HOSTS = ["*"]
# CSRF_TRUSTED_ORIGINS = environ.get("CSRF_TRUSTED_ORIGINS", "http://localhost:8000")

SECRET_KEY = environ.get("SECRET_KEY")

# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases


default = {
    "ENGINE": environ.get("SQL_ENGINE"),
    "NAME": environ.get("SQL_DATABASE"),
    "USER": environ.get("SQL_USER"),
    "PASSWORD": environ.get("SQL_PASSWORD"),
    "HOST": environ.get("SQL_HOST"),
    "PORT": int(environ.get("SQL_PORT")),
}

DATABASES = {
    "default": default,
}

# JWT Settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": datetime.timedelta(days=3),
    "REFRESH_TOKEN_LIFETIME": datetime.timedelta(days=30 * 2),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": datetime.timedelta(hours=1),
    "SLIDING_TOKEN_REFRESH_LIFETIME": datetime.timedelta(hours=3),
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [environ.get("REDIS_HOST", "redis://redis:6379/4")]},
    },
}

CELERY_BROKER_URL = environ.get("CELERY_BROKER", "redis://redis_service:6379/0")
CELERY_RESULT_BACKEND = environ.get("CELERY_BROKER", "redis://redis_service:6379/0")

CORS_ALLOW_ALL_ORIGINS = True

MJ_APIKEY_PUBLIC = environ.get("MJ_APIKEY_PUBLIC")
MJ_APIKEY_PRIVATE = environ.get("MJ_APIKEY_PRIVATE")

ONE_SIGNAL_APP_ID = environ.get("ONE_SIGNAL_APP_ID")
ONE_SIGNAL_USER_KEY = environ.get("ONE_SIGNAL_USER_KEY")
ONE_SIGNAL_REST_API_KEY = environ.get("ONE_SIGNAL_REST_API_KEY")

USE_AWS = bool(int(environ.get("USE_AWS", "0")))
if USE_AWS:
    AWS_ACCESS_KEY_ID = environ.get("AWS_ACCESS_KEY_ID", None)
    AWS_SECRET_ACCESS_KEY = environ.get("AWS_SECRET_ACCESS_KEY", None)
    AWS_S3_REGION_NAME = environ.get("AWS_S3_REGION_NAME", None)
    AWS_STORAGE_BUCKET_NAME = environ.get("AWS_STORAGE_BUCKET_NAME", None)
    AWS_DEFAULT_ACL = environ.get("AWS_DEFAULT_ACL", None)
    AWS_QUERYSTRING_AUTH = False

    if (
        not AWS_ACCESS_KEY_ID
        or not AWS_SECRET_ACCESS_KEY
        or not AWS_S3_REGION_NAME
        or not AWS_STORAGE_BUCKET_NAME
    ):
        raise ValueError("One of the next params doesn't exist")

    STORAGES = {
        # Media file (image) management
        "default": {
            "BACKEND": "backend.settings.configs.storages.MediaStorage",
        },
        # CSS and JS file management
        "staticfiles": {
            "BACKEND": "backend.settings.configs.storages.StaticStorage",
        },
    }

SENTRY_DNS = environ.get("SENTRY_DNS")

COURIER_AUTH_TOKEN = environ.get("COURIER_AUTH_TOKEN", "")

FIREBASE_APP_WEB_API_KEY = environ.get("FIREBASE_APP_WEB_API_KEY")
FIREBASE_APP_DOMAINE = environ.get("FIREBASE_APP_DOMAINE")

sentry_sdk.init(
    dsn=SENTRY_DNS,
    traces_sample_rate=1.0,
    send_default_pii=True,
    release="production",
)

CELERY_TASK_ALWAYS_EAGER = True  # Exécute les tâches immédiatement de manière synchrone
CELERY_TASK_EAGER_PROPAGATES = True  # Propage les exceptions
CELERY_BROKER_URL = 'memory://'  # Broker en mémoire
CELERY_RESULT_BACKEND = 'cache+memory://'  # Backend en mémoire

# print("⚠️  MODE DEV: Celery en mode synchrone - Redis non requis")