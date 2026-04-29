from django.urls import path
from .views import check_plagiarism_api

urlpatterns = [
    path("check/", check_plagiarism_api, name="check-plagiarism"),
]