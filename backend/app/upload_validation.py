"""Validate uploads before storage or any expensive pipeline stage."""
from io import BytesIO
from pathlib import PurePosixPath
import warnings

from fastapi import HTTPException

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_PDF_PAGES = 200
MAX_IMAGE_PIXELS = 25_000_000


def validate_upload(data: bytes, filename: str, content_type: str | None) -> str:
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (max 25 MB)")
    suffix = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
    formats = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    expected = formats.get(suffix)
    if expected is None:
        raise HTTPException(415, "Supported file types: PDF, PNG and JPEG")
    declared = (content_type or "application/octet-stream").split(";", 1)[0].strip().lower()
    if declared not in (expected, "application/octet-stream"):
        raise HTTPException(415, "Declared MIME type does not match the filename")
    try:
        if expected == "application/pdf":
            import fitz

            if not data.startswith(b"%PDF-"):
                raise ValueError("Invalid PDF signature")
            with fitz.open(stream=data, filetype="pdf") as doc:
                if doc.needs_pass or not 1 <= doc.page_count <= MAX_PDF_PAGES:
                    raise ValueError("PDF must be unencrypted and contain 1 to 200 pages")
        else:
            from PIL import Image

            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(data)) as image:
                    if image.format != ("PNG" if expected == "image/png" else "JPEG"):
                        raise ValueError("Image signature does not match its extension")
                    if image.width * image.height > MAX_IMAGE_PIXELS:
                        raise ValueError("Image exceeds 25 million pixels")
                    image.verify()
    except Exception as exc:
        raise HTTPException(400, "Invalid, encrypted or excessive document; use PDF (1-200 pages), PNG or JPEG (up to 25 million pixels)") from exc
    return expected
