# -*- coding: utf-8 -*-
"""
Created on 12/09/2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.utils.deconstruct import deconstructible
from storages.backends.s3boto3 import S3Boto3Storage


@deconstructible
class StaticStorage(S3Boto3Storage):
    """Querystring auth must be disabled so that url() returns a consistent output."""

    querystring_auth = False
    location = 'statics'


@deconstructible
class MediaStorage(S3Boto3Storage):
    location = 'medias'
    querystring_auth = False
