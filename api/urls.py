from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.contrib import admin
from django.urls import path, include

from .views import (
    InferMetadataView,
    ValidateMetadataView,
    SubmitMetadataView,
    RecordListView,
    RecordDetailView,
)

urlpatterns = [
    # 1. Inference
    path('infer/', InferMetadataView.as_view(), name='api-infer'),
    # 2. Validation
    path('validate/', ValidateMetadataView.as_view(), name='api-validate'),
    # 3. Submission
    path('submit/', SubmitMetadataView.as_view(), name='api-submit'),
    # 4. Record retrieval
    path('records/', RecordListView.as_view(), name='api-record-list'),
    path('records/<uuid:record_id>/', RecordDetailView.as_view(), name='api-record-detail'),
    # OpenAPI schema and Swagger UI
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
]