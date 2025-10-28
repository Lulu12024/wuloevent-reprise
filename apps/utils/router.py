# -*- coding: utf-8 -*-
"""
Created on April 26 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.utils import views
from apps.utils.views import VariableListView

simple_urls = [
    path("variables/", VariableListView.as_view()),
    path("statistics/", views.StatsViewSet.as_view({"get": "statistics"})),
]

router = DefaultRouter()
router.register(r"countries", views.CountriesViewSet, basename="CountriesViewSet")
router.register(
    r"variable-values", views.VariableValueViewSet, basename="VariableValueViewSet"
)
router.register(r"errors", views.ErrorsViewSet, basename="ErrorsViewSet")

urls_patterns = router.urls
urls_patterns += simple_urls
