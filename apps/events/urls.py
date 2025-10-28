# -*- coding: utf-8 -*-
"""
Created on April 29, 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.urls import path

from apps.events import views
from apps.events.router import router

urlpatterns = [
    path("favourite-events/", views.FavouriteEventView.as_view()),
    path("favourite-event-types/", views.FavouriteEventTypeView.as_view())
]

urlpatterns += router.urls
