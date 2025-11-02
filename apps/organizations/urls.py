from django.urls import path

from apps.organizations.router import urls_patterns
from apps.organizations.views import (
    OrganizationFollowersView, 
    OrganizationFollowedView,
    OrganizationFollowView, 
    OrganizationUnFollowView,
    ScanETicketView
)
from apps.organizations.views.ephemeral_event_views import (
    EphemeralEventCreateAPIView,
    EphemeralEventViewSet,
)

urlpatterns = [
    # === URLs Organisations existantes ===
    path("organizations/<str:organization_pk>/followers",
         OrganizationFollowersView.as_view()),
    path("organizations/followeds", 
         OrganizationFollowedView.as_view()),
    path("organizations/<str:organization_pk>/follow",
         OrganizationFollowView.as_view()),
    path("organizations/<str:organization_pk>/unfollow",
         OrganizationUnFollowView.as_view()),
    path("organizations/<str:organization_pk>/scann-eticket/",
         ScanETicketView.as_view()),

    
    # Création d'événement éphémère
    path('api/super-sellers/events/ephemeral/',
        EphemeralEventCreateAPIView.as_view(),name='create-ephemeral-event'),
    

    path('api/super-sellers/events/ephemeral/',
        EphemeralEventViewSet.as_view({'get': 'list'}),name='ephemeral-events-list'),
    
    # Détails d'un événement éphémère
    path('api/super-sellers/events/ephemeral/<str:pk>/',
         EphemeralEventViewSet.as_view({'get': 'retrieve'}),name='ephemeral-events-detail'),
    
    # Statistiques d'un événement éphémère
    path(
        'api/super-sellers/events/ephemeral/<str:pk>/statistics/',
        EphemeralEventViewSet.as_view({'get': 'statistics'}),name='ephemeral-events-statistics'),
]

urlpatterns += urls_patterns