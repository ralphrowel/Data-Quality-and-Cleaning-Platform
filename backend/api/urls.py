"""URL Routing for REST API endpoints.

Phase 7: V7.1 – V7.6
"""

from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from api import views

urlpatterns = [
    # OpenAPI Schema & Swagger Documentation
    path("schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="api-schema"), name="api-redoc"),

    # Core REST Endpoints
    path("health/", views.health_check, name="api-health"),
    path("datasets/", views.datasets_collection, name="api-datasets"),
    path("datasets/<str:dataset_id>/", views.dataset_detail, name="api-dataset-detail"),
    path("datasets/<str:dataset_id>/profile/", views.dataset_profile, name="api-dataset-profile"),
    path("datasets/<str:dataset_id>/quality/", views.dataset_quality, name="api-dataset-quality"),
    path("datasets/<str:dataset_id>/clean/", views.dataset_clean, name="api-dataset-clean"),
    path("datasets/<str:dataset_id>/export/", views.dataset_export, name="api-dataset-export"),
]

