import logging

from django.db import models

from apps.utils.utils import _upload_to
from commons.models import AbstractCommonBaseModel

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


class Sponsor(AbstractCommonBaseModel):
    name = models.CharField(max_length=220)
    logo = models.ImageField(upload_to=_upload_to)
    url = models.CharField(max_length=255, null=True, blank=True)
    active = models.BooleanField(default=False)

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        verbose_name = "Sponsor"
        verbose_name_plural = "Sponsors"
