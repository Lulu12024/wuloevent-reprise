# -*- coding: utf-8 -*-
"""
Created on 14/11/2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from dotenv import dotenv_values

environ = dotenv_values(".env")


EMAIL_BACKEND = environ.get("EMAIL_BACKEND")
EMAIL_HOST = environ.get("EMAIL_HOST")
EMAIL_USE_TLS = True
EMAIL_PORT = environ.get("EMAIL_PORT")
EMAIL_HOST_USER = environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = environ.get("EMAIL_HOST_PASSWORD")
EMAIL_NO_REPLY = environ.get("EMAIL_NO_REPLY")
