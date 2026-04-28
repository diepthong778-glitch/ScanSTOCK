# SCANSTOCK

SCANSTOCK is an AI-powered document scanning and analysis system built with Django. It supports document scanning, OCR extraction, AI document recognition, fake document risk analysis, plagiarism similarity checking, PDF export, and scan history management.

## Main Features

- Document image upload
- Mobile camera capture
- Auto paper boundary detection
- Perspective correction
- Image enhancement modes: black and white, gray, color, OCR optimized
- OCR text extraction with Tesseract
- OCR confidence score
- AI-assisted document classification
- Fake document risk score with suspicious indicators
- Plagiarism similarity checking
- Top matched reference documents
- Scanned JPG and PDF export
- Scan history and result detail modal
- Reference document management
- Django admin management
- Premium responsive web UI

## Tech Stack

Backend:
- Python
- Django 5.2 LTS
- Django REST Framework

Computer Vision:
- OpenCV
- NumPy
- Pillow

OCR:
- Tesseract OCR
- pytesseract

AI / ML:
- scikit-learn
- TF-IDF
- Logistic Regression
- joblib

Plagiarism:
- RapidFuzz
- TF-IDF cosine similarity

Export:
- img2pdf

Database:
- SQLite for development
- Optional PostgreSQL for production

## System Architecture

User uploads or captures a document image.

SCANSTOCK then processes it through this pipeline:

1. Django receives and stores the uploaded file.
2. OpenCV validates image quality.
3. Multiple boundary detection strategies find the document paper.
4. Perspective correction creates a scanned document view.
5. Image enhancement prepares both display output and OCR-optimized output.
6. Tesseract OCR extracts text and confidence information.
7. Hybrid classification recognizes the document type.
8. Risk analysis checks suspicious indicators.
9. The result is saved to the database and returned through the API/UI.

## Folder Structure

```text
scanstock/          Django project settings, root routes, frontend page views
scanner/            Document scanner API, models, serializers, services
plagiarism/         Reference documents, plagiarism API, matching services
ai_core/            AI classification, risk analyzer, training script
media/              Uploaded and generated files
datasets/           Training CSV files
models_ai/          Trained ML model files
static/             CSS, JavaScript, icons, images
templates/          Django frontend templates
```

## Installation Guide for Windows

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Install Tesseract OCR:

- Recommended Windows installer: UB Mannheim Tesseract build
- Example path:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

Configure `TESSERACT_CMD` if your path is different:

```powershell
$env:TESSERACT_CMD="C:\Program Files\Tesseract-OCR\tesseract.exe"
```

Run database migrations:

```powershell
python manage.py migrate
```

Create an admin user:

```powershell
python manage.py createsuperuser
```

Run the development server:

```powershell
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Environment and Configuration

Important settings:

- `TESSERACT_CMD`: path to the Tesseract executable.
- `MEDIA_ROOT`: stores uploaded and generated scanner files.
- `MEDIA_URL`: serves media files during development.
- `DEBUG`: enabled for local development.

Default media configuration:

```python
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

## Local OCR Pipeline Test

SCANSTOCK also includes a clean local OCR pipeline that can be tested without calling the Django API.

Main function:

```python
from services.pipeline_service import process_document_image

result = process_document_image(image_bytes, lang="eng")
```

Pipeline files:

```text
services/image_service.py
services/ocr_service.py
services/classification_service.py
services/extraction_service.py
services/pipeline_service.py
```

Install the core OCR pipeline dependencies:

```powershell
pip install opencv-python numpy pillow pytesseract
```

Install Tesseract separately on Windows:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

Run a local image test:

```powershell
python scripts/run_pipeline_test.py samples/invoice.jpg
```

The pipeline returns a stable dictionary containing:

```json
{
  "success": true,
  "documentType": "invoice",
  "rawText": "...",
  "cleanText": "...",
  "structuredData": {},
  "confidence": 0.75,
  "warnings": [],
  "processingSteps": []
}
```

## API Endpoints

Health:

```http
GET /api/health
```

Response:

```json
{
  "status": "ok",
  "tesseractAvailable": true
}
```

Production-style document API:

```http
POST /api/documents/scan
POST /api/documents/extract-text
POST /api/documents/classify
```

`POST /api/documents/scan` accepts multipart form data:

```text
file: image file
lang: eng | vie | eng+vie
```

`POST /api/documents/extract-text` accepts multipart form data:

```text
file: image file
lang: eng | vie | eng+vie
```

`POST /api/documents/classify` accepts JSON:

```json
{
  "text": "Invoice total amount tax payment"
}
```

Scanner:

```http
POST /api/scanner/scan/
```

Multipart form fields:

```text
image: uploaded image file
mode: bw | gray | color | ocr
lang: eng | vie | eng+vie
```

Plagiarism:

```http
POST /api/plagiarism/check/
```

JSON body:

```json
{
  "text": "Text to compare with reference documents."
}
```

The plagiarism endpoint also accepts optional offline sources:

```json
{
  "text": "Text to check",
  "sources": [
    "Offline source text 1",
    "Offline source text 2"
  ]
}
```

If `sources` are not provided, SCANSTOCK does not claim internet plagiarism checking. It returns a note explaining that external internet checking is unavailable offline and performs internal/database-based analysis where available.

## Curl Examples

Health:

```bash
curl http://127.0.0.1:8000/api/health
```

Scan an image:

```bash
curl -X POST "http://127.0.0.1:8000/api/documents/scan?lang=eng" \
  -F "file=@samples/invoice.jpg"
```

Extract OCR text:

```bash
curl -X POST "http://127.0.0.1:8000/api/documents/extract-text?lang=eng" \
  -F "file=@samples/invoice.jpg"
```

Classify text:

```bash
curl -X POST http://127.0.0.1:8000/api/documents/classify \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"Invoice total amount tax payment\"}"
```

Check plagiarism with provided sources:

```bash
curl -X POST http://127.0.0.1:8000/api/plagiarism/check \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"This is the submitted text\",\"sources\":[\"This is one offline source text\"]}"
```

## Backend Run Command

This project already uses Django, so the backend runs with:

```powershell
python manage.py runserver
```

It can also run through ASGI with uvicorn:

```powershell
uvicorn app.main:app --reload
```

FastAPI is not introduced because changing framework would break the existing SCANSTOCK structure. `app.main:app` is an ASGI entrypoint that loads the existing Django application.

## Example Scanner Response

```json
{
  "id": 1,
  "status": "done",
  "scanned_image_url": "http://127.0.0.1:8000/media/scanner/results/scan_1.jpg",
  "pdf_file_url": "http://127.0.0.1:8000/media/scanner/pdfs/scan_1.pdf",
  "ocr_text": "Invoice tax code VAT total amount...",
  "document_type": "invoice",
  "document_confidence": 0.82,
  "classification_info": {
    "method": "ai_model",
    "matched_signals": ["invoice", "vat", "tax code"]
  },
  "quality_info": {
    "quality_score": 0.78,
    "quality_level": "good",
    "quality_warnings": []
  },
  "boundary_info": {
    "paper_detected": true,
    "boundary_confidence": 0.86
  },
  "ocr_info": {
    "ocr_confidence": 0.74,
    "ocr_language": "eng+vie"
  },
  "fake_risk_score": 0.18,
  "fake_risk_level": "low",
  "fake_reasons": [
    "No strong suspicious indicators were detected."
  ],
  "manual_review_recommended": false
}
```

## Example Plagiarism Response

```json
{
  "id": 1,
  "similarity_percent": 72.4,
  "risk_level": "high",
  "matched_document": {
    "id": 2,
    "title": "Reference Contract",
    "source": "Internal"
  },
  "matched_excerpt": "Matched text excerpt...",
  "matches": [
    {
      "title": "Reference Contract",
      "score": 72.4,
      "excerpt": "Matched text excerpt..."
    }
  ]
}
```

## AI Model Training

Training dataset:

```text
datasets/document_training.csv
```

Required columns:

```text
text,label
```

Supported labels:

```text
cccd_id_card
invoice
contract
resume
medical_document
bank_statement
school_document
receipt
unknown
```

Train the model:

```powershell
python ai_core/train_document_classifier.py
```

Output model:

```text
models_ai/document_classifier.joblib
```

## Accuracy Note

SCANSTOCK does not claim 100% accuracy.

OCR, document classification, risk analysis, and plagiarism similarity are AI-assisted estimates. The system returns confidence scores, risk scores, quality warnings, and suspicious indicators so users can make better review decisions.

Important documents should be manually reviewed.

This result is not a legal verification.

## Future Improvements

- Manual four-point crop adjustment
- Better OCR engine fallback
- Real semantic plagiarism search
- Multi-page PDF scanning
- User authentication
- Cloud deployment
- PostgreSQL production database
- Docker setup
- Advanced forgery detection model
- Full mobile PWA support
- PDF and DOCX text upload for plagiarism checking

## Author

Author: Diệp Nguyễn Minh Thông

Project: SCANSTOCK

Purpose: Academic project / portfolio project
