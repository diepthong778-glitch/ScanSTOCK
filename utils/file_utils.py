ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff"}
MAX_UPLOAD_BYTES = 12 * 1024 * 1024


def validate_uploaded_image(uploaded_file) -> tuple[bool, str]:
    if uploaded_file is None:
        return False, "Missing image file. Upload using multipart field name 'file'."

    content_type = getattr(uploaded_file, "content_type", "") or ""
    if content_type and content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        return False, "Unsupported file type. Please upload a JPG, PNG, WEBP, BMP, or TIFF image."

    size = getattr(uploaded_file, "size", 0) or 0
    if size <= 0:
        return False, "Uploaded file is empty."
    if size > MAX_UPLOAD_BYTES:
        return False, "Uploaded image is too large. Maximum size is 12 MB."

    return True, ""
