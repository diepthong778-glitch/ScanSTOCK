from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from plagiarism.models import PlagiarismCheck, ReferenceDocument
from scanner.models import ScanJob


def landing(request):
    return render(request, "landing.html")


def dashboard(request):
    total_scans = ScanJob.objects.count()
    recognized_documents = ScanJob.objects.exclude(document_type__in=["", "unknown"]).count()
    high_risk_documents = ScanJob.objects.filter(fake_risk_level="high").count()
    plagiarism_checks = PlagiarismCheck.objects.count()

    context = {
        "stats": {
            "total_scans": total_scans,
            "recognized_documents": recognized_documents,
            "high_risk_documents": high_risk_documents,
            "plagiarism_checks": plagiarism_checks,
        },
        "recent_scans": ScanJob.objects.order_by("-created_at")[:6],
        "recent_checks": PlagiarismCheck.objects.select_related("matched_document").order_by("-created_at")[:6],
    }
    return render(request, "dashboard.html", context)


def scanner_page(request):
    return render(request, "scanner.html")


def plagiarism_page(request):
    return render(request, "plagiarism.html")


def history_page(request):
    scans = ScanJob.objects.order_by("-created_at")
    return render(request, "history.html", {"scans": scans})


def reference_documents_page(request):
    query = request.GET.get("q", "").strip()
    documents = ReferenceDocument.objects.all()
    if query:
        documents = documents.filter(
            Q(title__icontains=query) | Q(source__icontains=query) | Q(content__icontains=query)
        )

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        source = request.POST.get("source", "").strip()
        content = request.POST.get("content", "").strip()
        if not title or not content:
            messages.error(request, "Title and content are required.")
        else:
            ReferenceDocument.objects.create(title=title, source=source, content=content)
            messages.success(request, "Reference document added.")
            return redirect("reference-documents")

    return render(
        request,
        "reference_documents.html",
        {"documents": documents, "query": query},
    )


@require_POST
def delete_reference_document(request, pk):
    document = get_object_or_404(ReferenceDocument, pk=pk)
    document.delete()
    messages.success(request, "Reference document deleted.")
    return redirect("reference-documents")


@require_POST
def delete_scan_job(request, pk):
    scan = get_object_or_404(ScanJob, pk=pk)
    for file_field in (scan.original_image, scan.scanned_image, scan.pdf_file):
        if file_field:
            file_field.delete(save=False)
    scan.delete()
    messages.success(request, "Scan deleted.")
    return redirect("history")
