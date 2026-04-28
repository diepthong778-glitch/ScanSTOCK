from django.urls import path

from plagiarism.views import PlagiarismCheckAPIView


urlpatterns = [
    path("check", PlagiarismCheckAPIView.as_view(), name="plagiarism-check-no-slash"),
    path("check/", PlagiarismCheckAPIView.as_view(), name="plagiarism-check"),
]
