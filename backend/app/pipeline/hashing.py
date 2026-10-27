"""Exact (sha256) and perceptual (pHash) fingerprints for duplicate detection across applications."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path

from PIL import Image

PDF_EXT = {".pdf"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _first_page_image(path: Path) -> Image.Image | None:
    ext = path.suffix.lower()
    if ext in PDF_EXT:
        import pymupdf

        with pymupdf.open(path) as doc:
            if doc.page_count == 0:
                return None
            pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(1, 1))
            return Image.open(io.BytesIO(pix.tobytes("png")))
    if ext in IMAGE_EXT:
        return Image.open(path)
    return None


def phash(path: str | Path) -> str | None:
    """64-bit perceptual hash as 16 hex chars (first page rendered for PDFs); None for non-visual files."""
    import imagehash

    try:
        img = _first_page_image(Path(path))
    except Exception:  # unreadable / corrupt file
        return None
    if img is None:
        return None
    return str(imagehash.phash(img.convert("RGB")))


def phash_distance(a: str | None, b: str | None) -> int | None:
    """Hamming distance between two hex pHashes (0 = identical; <= 8 = near-duplicate)."""
    if not a or not b or len(a) != len(b):
        return None
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def is_near_duplicate(a: str | None, b: str | None, threshold: int = 8) -> bool:
    d = phash_distance(a, b)
    return d is not None and d <= threshold
