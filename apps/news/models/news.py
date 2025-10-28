import logging

from django.db import models

from apps.notifications.utils.firebase import FirebaseDynamicLinkGenerator
from commons.models import AbstractCommonBaseModel
from commons.utils import _upload_to

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class New(AbstractCommonBaseModel):
    title = models.CharField(max_length=255, verbose_name="Titre")
    description = models.TextField(null=False, blank=False, verbose_name="Description")
    cover_image = models.ImageField(upload_to=_upload_to, verbose_name="Image de couverture")

    dynamic_link = models.CharField(max_length=512, verbose_name="Lien dynamique")

    expired_at = models.DateField("Date d'expiration")
    status = models.BooleanField(default=True, verbose_name="Actif")

    event = models.ForeignKey(to='events.Event', related_name="news", null=True, blank=True, on_delete=models.SET_NULL,
                              verbose_name="Evenement relatif")

    def get_dynamic_link(self):
        event_link = f"https://wuloevents.com/news/{self.pk}"
        if self.dynamic_link:
            return self.dynamic_link
        generator = FirebaseDynamicLinkGenerator()
        link = generator.generate(
            link=event_link,
            meta_tag_info={
                "socialTitle": self.title,
                "socialDescription": self.description,
                "socialImageLink": self.get_cover_image_url,
            },
        )
        self.dynamic_link = link
        self.save(update_fields=["dynamic_link"])
        return link

    @property
    def get_cover_image_url(self):
        if self.cover_image and hasattr(self.cover_image, "url"):
            return self.cover_image.url
        return None

    @property
    def get_entity_info(self):
        return {"name": self.name}

    class Meta:
        verbose_name = "Actualité"
        verbose_name_plural = "Actualités"

    def __str__(self):
        return self.title
