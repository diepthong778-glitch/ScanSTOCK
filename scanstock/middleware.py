from django.http import HttpResponse


class LocalhostCorsMiddleware:
    allowed_origins = {
        "http://localhost:3000",
        "http://localhost:5173",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin")
        if request.method == "OPTIONS" and origin in self.allowed_origins:
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        if origin in self.allowed_origins:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-CSRFToken"
            response["Access-Control-Allow-Credentials"] = "true"
        return response
