from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import PlagiarismCheck
from .services import check_plagiarism


@api_view(["POST"])
def check_plagiarism_api(request):
    input_text = request.data.get("text", "").strip()

    if not input_text:
        return Response(
            {"error": "Vui lòng nhập nội dung cần check."},
            status=status.HTTP_400_BAD_REQUEST
        )

    result = check_plagiarism(input_text)

    matched_doc = result["matched_document"]

    check = PlagiarismCheck.objects.create(
        input_text=input_text,
        similarity_percent=result["similarity_percent"],
        matched_document=matched_doc,
        matched_excerpt=result["matched_excerpt"]
    )

    return Response({
        "message": "Check đạo văn thành công.",
        "check_id": check.id,
        "similarity_percent": check.similarity_percent,
        "matched_document": matched_doc.title if matched_doc else None,
        "matched_excerpt": check.matched_excerpt
    })