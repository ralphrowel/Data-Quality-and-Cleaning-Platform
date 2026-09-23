"""URL Routing for REST API endpoints.

Phase 7: V7.1 – V7.6
"""

from django.urls import path
from api import views

urlpatterns = [
    path("health/", views.health_check, name="api-health"),
    path("datasets/", views.datasets_collection, name="api-datasets"),
    path("datasets/<str:dataset_id>/", views.dataset_detail, name="api-dataset-detail"),
    path("datasets/<str:dataset_id>/profile/", views.dataset_profile, name="api-dataset-profile"),
    path("datasets/<str:dataset_id>/quality/", views.dataset_quality, name="api-dataset-quality"),
    path("datasets/<str:dataset_id>/clean/", views.dataset_clean, name="api-dataset-clean"),
    path("datasets/<str:dataset_id>/export/", views.dataset_export, name="api-dataset-export"),
]
