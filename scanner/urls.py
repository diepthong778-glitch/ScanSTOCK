from django.urls import path
from .views import scan_document_api

urlpatterns = [
    path("scan/", scan_document_api, name="scan-document"),
]