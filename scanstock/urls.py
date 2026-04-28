"""
URL configuration for scanstock project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from scanstock.api_views import HealthAPIView
from scanstock import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('scanner/', views.scanner_page, name='scanner-page'),
    path('plagiarism/', views.plagiarism_page, name='plagiarism-page'),
    path('history/', views.history_page, name='history'),
    path('history/<int:pk>/delete/', views.delete_scan_job, name='delete-scan-job'),
    path('reference-documents/', views.reference_documents_page, name='reference-documents'),
    path('reference-documents/<int:pk>/delete/', views.delete_reference_document, name='delete-reference-document'),
    path('admin/', admin.site.urls),
    path('api/health', HealthAPIView.as_view(), name='api-health'),
    path('api/health/', HealthAPIView.as_view(), name='api-health-slash'),
    path('api/documents/', include('scanner.document_urls')),
    path('api/scanner/', include('scanner.urls')),
    path('api/plagiarism/', include('plagiarism.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
