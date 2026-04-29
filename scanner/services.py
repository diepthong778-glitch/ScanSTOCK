from pathlib import Path
import cv2
import numpy as np
import pytesseract
import img2pdf
from PIL import Image
from django.conf import settings


def setup_tesseract():
    tesseract_path = Path(settings.TESSERACT_CMD)
    if tesseract_path.exists():
        pytesseract.pytesseract.tesseract_cmd = str(tesseract_path)


def order_points(points):
    rect = np.zeros((4, 2), dtype="float32")

    s = points.sum(axis=1)
    rect[0] = points[np.argmin(s)]
    rect[2] = points[np.argmax(s)]

    diff = np.diff(points, axis=1)
    rect[1] = points[np.argmin(diff)]
    rect[3] = points[np.argmax(diff)]

    return rect


def perspective_transform(image, points):
    rect = order_points(points)
    tl, tr, br, bl = rect

    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = int(max(width_a, width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = int(max(height_a, height_b))

    destination = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1]
    ], dtype="float32")

    matrix = cv2.getPerspectiveTransform(rect, destination)
    warped = cv2.warpPerspective(image, matrix, (max_width, max_height))

    return warped


def find_document_contour(image):
    ratio = image.shape[0] / 600.0
    resized = cv2.resize(image, (int(image.shape[1] / ratio), 600))

    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 150)

    contours, _ = cv2.findContours(
        edged.copy(),
        cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE
    )

    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

    for contour in contours:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

        if len(approx) == 4:
            return approx.reshape(4, 2) * ratio

    return None


def enhance_image(image, mode="bw"):
    if mode == "color":
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        merged = cv2.merge((l, a, b))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

    if mode == "gray":
        return denoised

    scanned = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        21,
        15
    )

    return scanned


def scan_image(input_path, output_path, mode="bw"):
    image = cv2.imread(str(input_path))

    if image is None:
        raise ValueError("Không đọc được ảnh.")

    contour = find_document_contour(image)

    if contour is not None:
        warped = perspective_transform(image, contour)
    else:
        warped = image

    enhanced = enhance_image(warped, mode=mode)

    success = cv2.imwrite(str(output_path), enhanced)
    if not success:
        raise ValueError("Không lưu được ảnh scan.")

    return output_path


def run_ocr(image_path, lang="eng+vie"):
    setup_tesseract()

    image = Image.open(image_path)
    text = pytesseract.image_to_string(
        image,
        lang=lang,
        config="--oem 3 --psm 6"
    )

    return text.strip()


def export_pdf(image_path, pdf_path):
    with open(pdf_path, "wb") as f:
        f.write(img2pdf.convert(str(image_path)))

    return pdf_path