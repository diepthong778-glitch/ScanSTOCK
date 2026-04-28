import os

from django.core.asgi import get_asgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scanstock.settings")

# Keeps the existing Django project while supporting:
# uvicorn app.main:app --reload
app = get_asgi_application()
