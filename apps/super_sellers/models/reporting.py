
"""
Created on November 05, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

from django.db import models
from django.conf import settings

class ReportFrequency(models.TextChoices):
    DAILY = "DAILY", "Quotidien"
    WEEKLY = "WEEKLY", "Hebdomadaire"
    MONTHLY = "MONTHLY", "Mensuel"

class ReportChannel(models.TextChoices):
    EMAIL = "EMAIL", "Email"
    WHATSAPP = "WHATSAPP", "WhatsApp"
    BOTH = "BOTH", "Email + WhatsApp"

class ReportFormat(models.TextChoices):
    PDF = "PDF", "PDF"
    CSV = "CSV", "CSV"

class SalesReportPreference(models.Model):
    """
    Préférences d’envoi automatique d’un super-vendeur.
    Un seul actif par organisation ou plusieurs.
    """
    super_seller = models.OneToOneField(
        "organizations.Organization",
        related_name="report_pref",
        on_delete=models.CASCADE
    )
    frequency = models.CharField(max_length=10, choices=ReportFrequency.choices, default=ReportFrequency.WEEKLY)
    channel = models.CharField(max_length=10, choices=ReportChannel.choices, default=ReportChannel.EMAIL)
    fmt = models.CharField(max_length=6, choices=ReportFormat.choices, default=ReportFormat.PDF)

    # Horodatage d’envoi
    time_of_day = models.TimeField(default="08:00")
    # 1=lundi … 7=dimanche (pour weekly)
    weekday = models.IntegerField(default=1) 
    # 1..28 pour monthly                
    day_of_month = models.IntegerField(default=1)            

    # Destinataires array of strings
    email_recipients = models.JSONField(default=list, blank=True)
    whatsapp_recipients = models.JSONField(default=list, blank=True)

    # Options de contenu
    include_by_seller = models.BooleanField(default=True)
    include_by_event = models.BooleanField(default=True)
    include_period_detail = models.BooleanField(default=True)
    include_graphs = models.BooleanField(default=False)

    active = models.BooleanField(default=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["super_seller"]),
            models.Index(fields=["active", "frequency"]),
        ]

class SalesReport(models.Model):
    """
    Archive de rapports générés.
    """
    super_seller = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="sales_reports")
    period_start = models.DateField()
    period_end = models.DateField()
    generated_at = models.DateTimeField(auto_now_add=True)

    # Chemins fichiers (S3 ou local)
    file_path = models.CharField(max_length=512, blank=True)    # ex: "reports/2025/11/ORG123_week_44.pdf"
    file_format = models.CharField(max_length=6, choices=ReportFormat.choices, default=ReportFormat.PDF)

    sent_via_email = models.BooleanField(default=False)
    sent_via_whatsapp = models.BooleanField(default=False)
    send_log = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["super_seller", "generated_at"]),
            models.Index(fields=["period_start", "period_end"]),
        ]
