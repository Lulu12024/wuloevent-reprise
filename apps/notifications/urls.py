# -*- coding: utf-8 -*-
"""
Created on April 29 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django.urls import path

from apps.notifications import views
from apps.notifications.router import router

namespace = 'notifications'

urlpatterns = [
    path(f'{namespace}/update-devices-list/', views.MobileDeviceView.as_view()),
    path(f'{namespace}/user-device-tokens/<user_id>/', views.UserDeviceTokensView.as_view(), name='user-device-tokens'),
]
urlpatterns += router.urls
