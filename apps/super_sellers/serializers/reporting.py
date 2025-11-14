"""
Created on November 5, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

from rest_framework import serializers
from apps.super_sellers.models.reporting import (
    SalesReportPreference, 
    ReportFrequency, 
    ReportChannel, 
    ReportFormat, 
    SalesReport
)

class SalesReportPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesReportPreference
        fields = (
            "frequency", "channel", "fmt", "time_of_day", "weekday", "day_of_month",
            "email_recipients", "whatsapp_recipients",
            "include_by_seller", "include_by_event", "include_period_detail", "include_graphs",
            "active", "last_sent_at",
        )

class SalesReportArchiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesReport
        fields = ("id", "period_start", "period_end", "generated_at", "file_path", "file_format",
                  "sent_via_email", "sent_via_whatsapp", "send_log")
