from rest_framework import status
from rest_framework.response import Response


def success_response(data: dict, http_status: int = status.HTTP_200_OK) -> Response:
    return Response(data, status=http_status)


def error_response(message: str, http_status: int = status.HTTP_400_BAD_REQUEST, **extra) -> Response:
    payload = {
        "success": False,
        "message": message,
    }
    payload.update(extra)
    return Response(payload, status=http_status)
