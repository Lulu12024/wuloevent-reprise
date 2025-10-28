# -*- coding: utf-8 -*-
"""
Created on April 26 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.contrib.auth.password_validation import CommonPasswordValidator
from django.core import validators
from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _


class MinimumLengthValidator:
    """
        Validate whether the password is of a minimum length.
        """

    def __init__(self, min_length=8):
        self.min_length = min_length

    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                _(f'This password is too short, it must contain at least {self.min_length} chars.'),
                code='password_too_short',
                params={'min_length': self.min_length},
            )


class CustomCommonPasswordValidator(CommonPasswordValidator):

    def validate(self, password, user=None):
        if password.lower().strip() in self.passwords:
            raise ValidationError(
                _(f'This password is a common password.'),
                code='password_too_common',
            )


@deconstructible
class PhoneNumberValidator(validators.RegexValidator):
    regex = r'^\+?1?\d{8,15}$'
    message = _(
        "Phone number must be entered in the format: '+111 99999999'. Up to 15 digits allowed."
    )
    flags = 0


class FileExtensionValidator(validators.FileExtensionValidator):
    message = "Extension de fichier non supportée."
    allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', 'jpeg', '.png']


@deconstructible
class FileMaxSizeValidator(object):
    message = 'La taille du fichier choisi (%(size)s) est trop grande. La limite est de %(allowed_size)s.'

    def __init__(self, *args, **kwargs):
        self.size = kwargs.pop('size', None)

    def __call__(self, value):
        """
        Check the extension, content type and file size.
        """

        # Check the file size
        filesize = len(value)
        if self.size and filesize > self.size:
            message = self.message % {
                'size': filesizeformat(filesize),
                'allowed_size': filesizeformat(self.size)
            }
            raise ValidationError(message)


def validate_file_extension(value):
    import os
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.pdf', '.doc', '.docx', '.jpg', 'jpeg', '.png']
    if not ext.lower() in valid_extensions:
        raise ValidationError('Extension de fichier non supportée.')


def validate_file_size(value):
    filesize = value.size

    if filesize > 10485760:
        raise ValidationError("The maximum file size that can be uploaded is 10MB")
    else:
        return value
