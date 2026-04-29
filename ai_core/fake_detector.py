from pathlib import Path
from PIL import Image, ExifTags
import cv2
import numpy as np


def check_image_quality(image_path):
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)

    if image is None:
        return 0.4, ["Không đọc được ảnh để kiểm tra chất lượng."]

    reasons = []
    risk = 0.0

    blur_score = cv2.Laplacian(image, cv2.CV_64F).var()

    if blur_score < 80:
        risk += 0.2
        reasons.append("Ảnh bị mờ, khó xác thực thông tin.")

    height, width = image.shape[:2]
    if width < 800 or height < 600:
        risk += 0.2
        reasons.append("Độ phân giải ảnh thấp.")

    return min(risk, 1.0), reasons


def check_metadata(image_path):
    reasons = []
    risk = 0.0

    try:
        image = Image.open(image_path)
        exif = image.getexif()

        if not exif:
            risk += 0.15
            reasons.append("Ảnh không có EXIF metadata. Có thể là ảnh đã qua chỉnh sửa hoặc tải lại.")

    except Exception:
        risk += 0.1
        reasons.append("Không đọc được metadata ảnh.")

    return min(risk, 1.0), reasons


def check_required_fields(document_type, text):
    normalized = text.lower()
    reasons = []
    risk = 0.0

    required_map = {
        "Căn cước công dân": [
            "căn cước",
            "số định danh",
            "ngày sinh",
            "quốc tịch",
            "quê quán"
        ],
        "Hóa đơn": [
            "hóa đơn",
            "tổng tiền",
            "mã số thuế"
        ],
        "Hợp đồng": [
            "hợp đồng",
            "bên a",
            "bên b",
            "điều khoản"
        ]
    }

    required_fields = required_map.get(document_type, [])

    if not required_fields:
        return 0.1, ["Chưa có mẫu kiểm tra riêng cho loại giấy tờ này."]

    missing = [field for field in required_fields if field not in normalized]

    if missing:
        risk += min(0.5, len(missing) * 0.15)
        reasons.append(f"Thiếu trường quan trọng: {', '.join(missing)}")

    return min(risk, 1.0), reasons


def fake_document_risk(image_path, document_type, ocr_text):
    total_risk = 0.0
    all_reasons = []

    checks = [
        check_image_quality(image_path),
        check_metadata(image_path),
        check_required_fields(document_type, ocr_text),
    ]

    for risk, reasons in checks:
        total_risk += risk
        all_reasons.extend(reasons)

    total_risk = min(total_risk, 1.0)

    if total_risk >= 0.65:
        level = "high"
    elif total_risk >= 0.35:
        level = "medium"
    else:
        level = "low"

    return {
        "risk_score": round(total_risk, 2),
        "risk_level": level,
        "reasons": all_reasons
    }
