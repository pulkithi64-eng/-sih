"""QR code decoding from images and rendered PDF pages (OpenCV QRCodeDetector)."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

PDF_EXT = {".pdf"}


def _decode_array(img: np.ndarray) -> list[str]:
    det = cv2.QRCodeDetector()
    out: list[str] = []
    try:
        ok, infos, _pts, _ = det.detectAndDecodeMulti(img)
        if ok:
            out.extend(s for s in infos if s)
    except cv2.error:
        pass
    if not out:
        try:
            s, _pts, _ = det.detectAndDecode(img)
            if s:
                out.append(s)
        except cv2.error:
            pass
    return out


def _variants(img: np.ndarray):
    yield img
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    yield cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)
    h, w = gray.shape[:2]
    if max(h, w) < 2400:
        yield cv2.resize(img, (w * 2, h * 2), interpolation=cv2.INTER_NEAREST)


def _render_pdf(path: Path, zoom: float, max_pages: int):
    import pymupdf

    with pymupdf.open(path) as doc:
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 4:
                arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            else:
                arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
            yield i + 1, arr


def decode_qr(path: str | Path, max_pages: int = 3) -> list[str]:
    """Return the distinct QR payload strings found in the file (images or first `max_pages` PDF pages)."""
    path = Path(path)
    found: list[str] = []

    def add(items):
        for s in items:
            if s not in found:
                found.append(s)

    if path.suffix.lower() in PDF_EXT:
        for zoom in (2.0, 3.0):
            for _page, arr in _render_pdf(path, zoom, max_pages):
                for v in _variants(arr):
                    res = _decode_array(v)
                    if res:
                        add(res)
                        break
            if found:
                break
        return found
    img = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return []
    for v in _variants(img):
        res = _decode_array(v)
        if res:
            add(res)
            break
    return found
