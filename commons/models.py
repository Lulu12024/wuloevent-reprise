from uuid import uuid4

from django.db import models
from django_softdelete.models import SoftDeleteModel


# Create your models here.


class AbstractCommonBaseModel(SoftDeleteModel):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False, unique=True)
    timestamp = models.DateTimeField(
        verbose_name="Date d' ajout", auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(
        verbose_name='Date de modification', auto_now_add=False, auto_now=True)
    active = models.BooleanField(
        verbose_name="Désigne si l' instance est active", default=True)

    class Meta:
        abstract = True

    def delete(self, cascade=None, *args, **kwargs):
        return super().delete(cascade, *args, **kwargs)

