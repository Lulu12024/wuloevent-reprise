
"""
Created on November 05, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr  
"""


from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.core.mail import EmailMessage
from apps.super_sellers.models.reporting import SalesReportPreference, ReportChannel
from apps.super_sellers.services.reporting import build_and_archive_report

import logging
logger = logging.getLogger(__name__)

def send_report_via_email(pref, report, super_seller):
    subject = f"Rapport de ventes - {super_seller.name}"
    body = f"Veuillez trouver ci-joint le rapport pour la période {report.period_start} - {report.period_end}."
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=f"WuloEvents <{getattr(settings,'EMAIL_NO_REPLY','no-reply@wulo')}>",
        to=pref.email_recipients or [super_seller.owner.email]
    )
    # attached file
    f = default_storage.open(report.file_path, "rb")
    try:
        email.attach(report.file_path.split("/")[-1], f.read(), "application/pdf")
    finally:
        f.close()
    email.send()
    return True

def send_report_via_whatsapp(pref, report, super_seller):
    """
    Envoi WhatsApp 
    """
    logger.info(f"[WHATSAPP] Send report {report.file_path} to {pref.whatsapp_recipients}")
    return True

@shared_task(bind=True)
def scan_and_send_scheduled_reports(self):
    """
    Tâche planifiée qui vérifie toutes les préférences
    et déclenche l’envoi si on tombe à l’heure voulue.
    """
    now = timezone.localtime()
    prefs = SalesReportPreference.objects.select_related("super_seller")\
        .filter(active=True, super_seller__organization_type="SUPER_SELLER")

    for pref in prefs:
        if str(pref.time_of_day)[:5] != now.strftime("%H:%M"):
            continue

        if pref.frequency == "DAILY":
            due = True
        elif pref.frequency == "WEEKLY":
            due = now.isoweekday() == (pref.weekday or 1)
        else:  # MONTHLY
            due = now.day == (pref.day_of_month or 1)

        if not due:
            continue

        # Eviter le double-envoi si envoie récent
        if pref.last_sent_at and (now - pref.last_sent_at).total_seconds() < 3600:
            continue

        super_seller = pref.super_seller
        report, _ = build_and_archive_report(super_seller, pref.frequency, pref.fmt)

        sent_email = sent_whatsapp = False
        if pref.channel in (ReportChannel.EMAIL, ReportChannel.BOTH):
            sent_email = send_report_via_email(pref, report, super_seller)
        if pref.channel in (ReportChannel.WHATSAPP, ReportChannel.BOTH):
            sent_whatsapp = send_report_via_whatsapp(pref, report, super_seller)

        report.sent_via_email = sent_email
        report.sent_via_whatsapp = sent_whatsapp
        report.send_log = {"email": sent_email, "whatsapp": sent_whatsapp}
        report.save(update_fields=["sent_via_email", "sent_via_whatsapp", "send_log"])

        pref.last_sent_at = now
        pref.save(update_fields=["last_sent_at"])
