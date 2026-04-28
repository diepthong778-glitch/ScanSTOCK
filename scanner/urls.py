from django.urls import path

from scanner.views import ScanDocumentAPIView


urlpatterns = [
    path("scan/", ScanDocumentAPIView.as_view(), name="scanner-scan"),
]
