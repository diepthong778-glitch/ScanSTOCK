from django.urls import path

from scanner.document_api import ClassifyDocumentAPIView, DocumentScanAPIView, ExtractTextAPIView


urlpatterns = [
    path("scan", DocumentScanAPIView.as_view(), name="documents-scan"),
    path("scan/", DocumentScanAPIView.as_view(), name="documents-scan-slash"),
    path("extract-text", ExtractTextAPIView.as_view(), name="documents-extract-text"),
    path("extract-text/", ExtractTextAPIView.as_view(), name="documents-extract-text-slash"),
    path("classify", ClassifyDocumentAPIView.as_view(), name="documents-classify"),
    path("classify/", ClassifyDocumentAPIView.as_view(), name="documents-classify-slash"),
]
