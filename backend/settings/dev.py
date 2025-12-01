# -*- coding: utf-8 -*-
"""
Created on June 15 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
import datetime
from pathlib import Path

from dotenv import dotenv_values

environ = dotenv_values(".env")

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = environ.get("DEBUG")

ALLOWED_HOSTS =["*"]

SECRET_KEY = environ.get("SECRET_KEY")

# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

default = {
    "ENGINE": environ.get("SQL_ENGINE", "django.db.backends.sqlite3"),
    "NAME": environ.get("SQL_DATABASE", BASE_DIR / "db.sqlite3"),
    "USER": environ.get("SQL_USER", "user"),
    "PASSWORD": environ.get("SQL_PASSWORD", "password"),
    "HOST": environ.get("SQL_HOST", "localhost"),
    "PORT": int(environ.get("SQL_PORT", "5432")),
}

DATABASES = {
    "default": default,
}
# JWT Settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": datetime.timedelta(days=20),
    "REFRESH_TOKEN_LIFETIME": datetime.timedelta(days=30),
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
    "SLIDING_TOKEN_LIFETIME": datetime.timedelta(days=20),
    "SLIDING_TOKEN_REFRESH_LIFETIME": datetime.timedelta(days=30),
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": ["redis://127.0.0.1:6379/4"]},
    },
}

CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"

MJ_APIKEY_PUBLIC = environ.get("MJ_APIKEY_PUBLIC")
MJ_APIKEY_PRIVATE = environ.get("MJ_APIKEY_PRIVATE")

ONE_SIGNAL_APP_ID = environ.get("ONE_SIGNAL_APP_ID")
ONE_SIGNAL_USER_KEY = environ.get("ONE_SIGNAL_USER_KEY")
ONE_SIGNAL_REST_API_KEY = environ.get("ONE_SIGNAL_REST_API_KEY")

COURIER_AUTH_TOKEN = environ.get("COURIER_AUTH_TOKEN")

FIREBASE_APP_WEB_API_KEY = environ.get("FIREBASE_APP_WEB_API_KEY")
FIREBASE_APP_DOMAINE = environ.get("FIREBASE_APP_DOMAINE")

USE_AWS = bool(int(environ.get("USE_AWS", "0")))
if USE_AWS:
    AWS_ACCESS_KEY_ID = environ.get("AWS_ACCESS_KEY_ID", None)
    AWS_SECRET_ACCESS_KEY = environ.get("AWS_SECRET_ACCESS_KEY", None)
    AWS_S3_REGION_NAME = environ.get("AWS_S3_REGION_NAME", None)
    AWS_STORAGE_BUCKET_NAME = environ.get("AWS_STORAGE_BUCKET_NAME", None)
    AWS_S3_ENDPOINT_URL = environ.get("AWS_S3_ENDPOINT_URL", None)
    AWS_DEFAULT_ACL = environ.get("AWS_DEFAULT_ACL", None)

    if (
            not AWS_ACCESS_KEY_ID
            or not AWS_SECRET_ACCESS_KEY
            or not AWS_STORAGE_BUCKET_NAME
    ):
        raise ValueError("One of the next params doesn't exist")

    STORAGES = {
        # CSS and JS file management
        "staticfiles": {
            "BACKEND": "backend.settings.configs.storages.StaticStorage",
        },
        # Media file (image) management
        "default": {
            "BACKEND": "backend.settings.configs.storages.MediaStorage",
        },
    }

SELLER_INVITATION_EXPIRY_DAYS = int(environ.get("SELLER_INVITATION_EXPIRY_DAYS", 7))
GUPSHUP_API_BASE = "https://api.gupshup.io"
GUPSHUP_API_KEY = environ.get("GUPSHUP_API_KEY")
GUPSHUP_WHATSAPP_SOURCE = environ.get("GUPSHUP_WHATSAPP_SOURCE")
GUPSHUP_APP_NAME = environ.get("GUPSHUP_APP_NAME")
GUPSHUP_TIMEOUT = 15