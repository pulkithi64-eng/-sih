"""Rendering helpers for the synthetic VeriSense dataset: official-looking PDFs, scans, infra photos.

All documents carry a footer "SYNTHETIC SPECIMEN" notice; every authority, institution and person is fictional.
"""
from __future__ import annotations

import io
import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import piexif
import pymupdf
import segno
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas

NAVY = HexColor("#0B2E59")
GREY = HexColor("#475569")
SPECIMEN = "SYNTHETIC SPECIMEN - generated for the VeriSense prototype; fictional issuer, not a real document"


# ----------------------------------------------------------------------------- fonts for raster work
def pil_font(size: int, bold=False, serif=False):
    names = (["timesbd.ttf", "DejaVuSerif-Bold.ttf"] if bold else ["times.ttf", "DejaVuSerif.ttf"]) if serif else \
            (["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["arial.ttf", "DejaVuSans.ttf"])
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    return ImageFont.load_default()


# ----------------------------------------------------------------------------- PDF documents
@dataclass
class DocSpec:
    authority: str                       # letterhead line 1 (issuer)
    authority_sub: list[str]             # letterhead lines 2..n (address, dept)
    title: str
    ref_label: str = "Ref. No."
    ref: str = ""
    date_label: str = "Date"
    date_text: str = ""
    to_lines: list[str] = field(default_factory=list)
    subject: str = ""
    paras_before: list[str] = field(default_factory=list)
    kv: list[tuple[str, str]] = field(default_factory=list)
    paras_after: list[str] = field(default_factory=list)
    sign: list[str] = field(default_factory=list)
    qr_payload: str | None = None
    emblem_color: str = "#0B2E59"
    stamp_text: str | None = None


def _emblem(c: canvas.Canvas, x, y, r, color):
    c.setStrokeColor(HexColor(color))
    c.setLineWidth(1.6)
    c.circle(x, y, r)
    c.circle(x, y, r * 0.72)
    for i in range(24):
        a = 2 * math.pi * i / 24
        c.line(x + r * 0.72 * math.cos(a), y + r * 0.72 * math.sin(a), x + r * math.cos(a), y + r * math.sin(a))
    c.setFillColor(HexColor(color))
    c.circle(x, y, r * 0.18, fill=1)


def _qr_image(payload: str) -> ImageReader:
    q = segno.make(payload, error="l", micro=False)
    buf = io.BytesIO()
    q.save(buf, kind="png", scale=6, border=2)
    buf.seek(0)
    return ImageReader(buf)


def draw_document(c: canvas.Canvas, spec: DocSpec, page_w=A4[0], page_h=A4[1]):
    left, right = 56, page_w - 56
    y = page_h - 52
    _emblem(c, left + 22, y - 16, 20, spec.emblem_color)
    if spec.qr_payload:
        size = 118
        c.drawImage(_qr_image(spec.qr_payload), right - size + 6, page_h - 34 - size, size, size)
        c.setFont("Helvetica", 6.5)
        c.setFillColor(GREY)
        c.drawCentredString(right - size / 2 + 6, page_h - 40 - size, "Scan to verify (issuer-signed)")
    text_x = left + 52
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 13.5)
    c.drawString(text_x, y - 6, spec.authority)
    c.setFont("Helvetica", 8.6)
    c.setFillColor(GREY)
    yy = y - 19
    for s in spec.authority_sub:
        c.drawString(text_x, yy, s)
        yy -= 10.5
    y = min(yy, page_h - 165 if spec.qr_payload else yy) - 6
    c.setStrokeColor(NAVY)
    c.setLineWidth(1.2)
    c.line(left, y, right, y)
    y -= 26
    c.setFillColor(HexColor("#0F172A"))
    if spec.ref or spec.date_text:
        c.setFont("Helvetica", 9.5)
        if spec.ref:
            c.drawString(left, y, f"{spec.ref_label}: {spec.ref}")
        if spec.date_text:
            c.drawRightString(right, y, f"{spec.date_label}: {spec.date_text}")
        y -= 24
    c.setFont("Helvetica-Bold", 13)
    for line in simpleSplit(spec.title, "Helvetica-Bold", 13, right - left):
        c.drawCentredString((left + right) / 2, y, line)
        y -= 17
    y -= 6
    c.setFont("Helvetica", 9.8)
    for s in spec.to_lines:
        c.drawString(left, y, s)
        y -= 12.5
    if spec.to_lines:
        y -= 6
    if spec.subject:
        c.setFont("Helvetica-Bold", 9.8)
        for line in simpleSplit("Subject: " + spec.subject, "Helvetica-Bold", 9.8, right - left):
            c.drawString(left, y, line)
            y -= 12.5
        y -= 6

    def paras(ps, y):
        c.setFont("Helvetica", 9.8)
        for p in ps:
            for line in simpleSplit(p, "Helvetica", 9.8, right - left):
                c.drawString(left, y, line)
                y -= 13
            y -= 6
        return y

    y = paras(spec.paras_before, y)
    if spec.kv:
        c.setStrokeColor(HexColor("#CBD5E1"))
        c.setLineWidth(0.5)
        top = y + 10
        for label, value in spec.kv:
            c.setFont("Helvetica-Bold", 9.6)
            c.drawString(left + 8, y, f"{label}:")
            c.setFont("Helvetica", 9.6)
            lines = simpleSplit(str(value), "Helvetica", 9.6, right - left - 210)
            for i, ln in enumerate(lines):
                c.drawString(left + 200, y - i * 12, ln)
            y -= 12 * max(1, len(lines)) + 5
        c.rect(left, y + 6, right - left, top - y - 6, stroke=1, fill=0)
        y -= 14
    y = paras(spec.paras_after, y)
    if spec.stamp_text:
        c.saveState()
        c.setStrokeColor(HexColor("#7C3AED"))
        c.setFillColor(HexColor("#7C3AED"))
        c.setLineWidth(1.4)
        c.translate(left + 110, max(y - 50, 120))
        c.rotate(12)
        c.circle(0, 0, 38)
        c.circle(0, 0, 30)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(0, 2, spec.stamp_text[:22])
        c.drawCentredString(0, -7, spec.stamp_text[22:44])
        c.restoreState()
    y -= 10
    c.setFont("Helvetica", 9.6)
    for i, s in enumerate(spec.sign):
        c.setFont("Helvetica-Bold" if i == 1 else "Helvetica", 9.6)
        c.drawRightString(right, max(y, 110) - i * 12.5, s)
    footer(c, page_w)


def footer(c, page_w):
    c.setFont("Helvetica-Oblique", 6.8)
    c.setFillColor(HexColor("#94A3B8"))
    c.drawCentredString(page_w / 2, 24, SPECIMEN)


def finalize_pdf(tmp: Path, out: Path, producer: str, creator: str, created: datetime, title: str):
    """Re-save via PyMuPDF with issuer-like metadata (CreationDate == ModDate, single revision)."""
    d = pymupdf.open(tmp)
    stamp = created.strftime("D:%Y%m%d%H%M%S+05'30'")
    d.set_metadata({"producer": producer, "creator": creator, "creationDate": stamp, "modDate": stamp,
                    "title": title, "author": "", "subject": "", "keywords": ""})
    d.save(out, garbage=3, deflate=True)
    d.close()
    tmp.unlink(missing_ok=True)


def make_pdf(out: Path, spec: DocSpec, producer: str, created: datetime, creator: str = "Issuer document service"):
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp.pdf")
    c = canvas.Canvas(str(tmp), pagesize=A4)
    draw_document(c, spec)
    c.showPage()
    c.save()
    finalize_pdf(tmp, out, producer, creator, created, spec.title)


def make_table_pdf(out: Path, title_lines: list[str], header: list[str], col_x: list[float], rows: list[list[str]],
                   summary: list[str], producer: str, created: datetime, sign: list[str]):
    """Landscape multi-page table (faculty roster)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp.pdf")
    pw, ph = landscape(A4)
    c = canvas.Canvas(str(tmp), pagesize=(pw, ph))
    per_page = 30
    pages = [rows[i:i + per_page] for i in range(0, len(rows), per_page)] or [[]]
    for pi, chunk in enumerate(pages):
        y = ph - 40
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 12.5)
        c.drawString(30, y, title_lines[0])
        c.setFont("Helvetica", 9)
        c.setFillColor(GREY)
        for s in title_lines[1:]:
            y -= 12
            c.drawString(30, y, s)
        y -= 22
        c.setFillColor(HexColor("#0F172A"))
        c.setFont("Helvetica-Bold", 8.6)
        for x, h in zip(col_x, header):
            c.drawString(x, y, h)
        c.setStrokeColor(HexColor("#94A3B8"))
        c.line(28, y - 4, pw - 28, y - 4)
        y -= 16
        c.setFont("Helvetica", 8.4)
        for r in chunk:
            for x, v in zip(col_x, r):
                c.drawString(x, y, v)
            y -= 13.2
        if pi == len(pages) - 1:
            y -= 10
            c.setFont("Helvetica-Bold", 9)
            for s in summary:
                c.drawString(30, y, s)
                y -= 12
            c.setFont("Helvetica", 9)
            for i, s in enumerate(sign):
                c.drawRightString(pw - 40, max(y - 10, 70) - i * 12, s)
        c.setFont("Helvetica", 7.5)
        c.drawRightString(pw - 30, 36, f"Page {pi + 1} of {len(pages)}")
        footer(c, pw)
        c.showPage()
    c.save()
    finalize_pdf(tmp, out, producer, "Institute ERP - faculty module", created, title_lines[0])


def tamper_pdf_incremental(path: Path, edits: list[tuple[str, str]], producer: str, mod: datetime,
                           fontname: str = "tiro"):
    """Simulate a forger editing values with a PDF/image editor: redact old text, write the new value in a
    different font at the same place, set editor Producer and later ModDate, save as an incremental update."""
    d = pymupdf.open(path)
    page = d[0]
    placements = []
    for old, new in edits:
        rects = page.search_for(old)
        if not rects:
            raise ValueError(f"text {old!r} not found for tampering")
        r = rects[0]
        page.add_redact_annot(r, fill=(1, 1, 1))
        placements.append((r, new))
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)
    for r, new in placements:
        page.insert_text((r.x0, r.y1 - 2.2), new, fontname=fontname, fontsize=10.2, color=(0.06, 0.09, 0.16))
    md = d.metadata
    md["producer"] = producer
    md["modDate"] = mod.strftime("D:%Y%m%d%H%M%S+05'30'")
    d.set_metadata(md)
    d.saveIncr()
    d.close()


# ----------------------------------------------------------------------------- scans
def render_page(pdf: Path, dpi=130, page=0) -> Image.Image:
    d = pymupdf.open(pdf)
    pix = d[page].get_pixmap(matrix=pymupdf.Matrix(dpi / 72, dpi / 72))
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    d.close()
    return img


def scan_effect(img: Image.Image, seed: int, angle: float = 0.35) -> Image.Image:
    rng = np.random.default_rng(seed)
    img = img.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=(250, 250, 248))
    arr = np.asarray(img).astype(np.float32)
    tint = np.array([248, 244, 232], np.float32) / 255.0
    arr = arr * tint
    h, w = arr.shape[:2]
    shade = np.linspace(1.0, 0.94, w)[None, :, None]
    arr = arr * shade + rng.normal(0, 3.2, arr.shape)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.55))
    return img


def jpeg_bytes(img: Image.Image, q: int, exif: bytes | None = None) -> bytes:
    buf = io.BytesIO()
    kw = {"quality": q}
    if exif:
        kw["exif"] = exif
    img.save(buf, "JPEG", **kw)
    return buf.getvalue()


def save_jpeg(img: Image.Image, out: Path, q: int, exif: bytes | None = None):
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(jpeg_bytes(img, q, exif))


def scanned_pdf(img: Image.Image, out: Path, producer: str, created: datetime, q=78):
    """Image-only PDF (as produced by an office scanner)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    d = pymupdf.open()
    page = d.new_page(width=A4[0], height=A4[1])
    page.insert_image(page.rect, stream=jpeg_bytes(img, q))
    stamp = created.strftime("D:%Y%m%d%H%M%S+05'30'")
    d.set_metadata({"producer": producer, "creator": "Scan to PDF", "creationDate": stamp, "modDate": stamp, "title": out.stem})
    d.save(out, garbage=3, deflate=True)
    d.close()


def paste_patch(img: Image.Image, box_xy: tuple[int, int], size: tuple[int, int], text: str, font_size: int,
                bg=(246, 241, 229), serif=True) -> Image.Image:
    """Forger's edit: cover a region and type a new value (fresh, never-compressed pixels)."""
    img = img.copy()
    patch = Image.new("RGB", size, bg)
    ImageDraw.Draw(patch).text((3, 2), text, font=pil_font(font_size, serif=serif), fill=(22, 24, 34))
    img.paste(patch, box_xy)
    return img


def find_text_box(pdf: Path, needle: str, dpi: int, page=0):
    d = pymupdf.open(pdf)
    rs = d[page].search_for(needle)
    d.close()
    if not rs:
        raise ValueError(needle)
    k = dpi / 72
    r = rs[0]
    return int(r.x0 * k), int(r.y0 * k), int(r.x1 * k), int(r.y1 * k)


# ----------------------------------------------------------------------------- EXIF
def _deg(v: float):
    v = abs(v)
    d = int(v)
    m = int((v - d) * 60)
    s = round(((v - d) * 60 - m) * 60 * 100)
    return ((d, 1), (m, 1), (s, 100))


def exif_bytes(taken: datetime | None, gps: dict | None, make="Samsung", model="Galaxy M34", software: str | None = None,
               modified: datetime | None = None) -> bytes:
    zeroth = {piexif.ImageIFD.Make: make.encode(), piexif.ImageIFD.Model: model.encode()}
    exif = {}
    if software:
        zeroth[piexif.ImageIFD.Software] = software.encode()
    if taken:
        ts = taken.strftime("%Y:%m:%d %H:%M:%S").encode()
        exif[piexif.ExifIFD.DateTimeOriginal] = ts
        exif[piexif.ExifIFD.DateTimeDigitized] = ts
        zeroth[piexif.ImageIFD.DateTime] = (modified or taken).strftime("%Y:%m:%d %H:%M:%S").encode()
    gps_ifd = {}
    if gps:
        gps_ifd = {piexif.GPSIFD.GPSLatitudeRef: b"N" if gps["lat"] >= 0 else b"S",
                   piexif.GPSIFD.GPSLatitude: _deg(gps["lat"]),
                   piexif.GPSIFD.GPSLongitudeRef: b"E" if gps["lng"] >= 0 else b"W",
                   piexif.GPSIFD.GPSLongitude: _deg(gps["lng"])}
    return piexif.dump({"0th": zeroth, "Exif": exif, "GPS": gps_ifd, "1st": {}, "thumbnail": None})


# ----------------------------------------------------------------------------- infra scenes
W, H = 1600, 1067


def _base(seed, wall=(226, 222, 210), floor=(150, 150, 146)):
    rng = random.Random(seed)
    img = Image.new("RGB", (W, H), wall)
    d = ImageDraw.Draw(img)
    horizon = int(H * 0.42)
    d.rectangle([0, horizon, W, H], fill=floor)
    for i in range(0, W, 80):  # floor tile joints in perspective
        d.line([(W / 2 + (i - W / 2) * 0.35, horizon), (i * 1.0, H)], fill=(136, 136, 132), width=1)
    for yy in (horizon + 40, horizon + 110, horizon + 220, horizon + 380):
        d.line([(0, yy), (W, yy)], fill=(138, 138, 134), width=1)
    d.rectangle([0, 0, W, 26], fill=(240, 240, 236))  # ceiling strip
    for x in range(120, W, 360):
        d.rectangle([x, 4, x + 180, 18], fill=(252, 252, 250))
    return img, d, rng, horizon


def _sign(d, x, y, text, size=30):
    f = pil_font(size, bold=True)
    tw = d.textlength(text, font=f)
    d.rectangle([x - 14, y - 10, x + tw + 14, y + size + 12], fill=(250, 250, 246), outline=(40, 60, 90), width=3)
    d.text((x, y), text, font=f, fill=(20, 40, 80))


def _finish(img, seed, blur=0.7, noise=3.0):
    rng = np.random.default_rng(seed)
    arr = np.asarray(img.filter(ImageFilter.GaussianBlur(blur))).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    vign = 1 - 0.18 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    arr = arr * vign[..., None] + rng.normal(0, noise, arr.shape)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def _row_layout(n_rows, per_row_list, horizon):
    """Yield (row_index, x_center, y_base, scale) for desk positions from back (small) to front (large)."""
    for r in range(n_rows):
        t = (r + 1) / n_rows
        scale = 0.45 + 0.55 * t
        y = horizon + 40 + int((H - horizon - 140) * (t ** 1.15))
        n = per_row_list[r]
        span = W * (0.55 + 0.38 * t)
        x0 = (W - span) / 2
        for i in range(n):
            yield r, x0 + span * (i + 0.5) / n, y, scale, span / n


def scene_computer_lab(n_monitors: int, seed: int, sign="COMPUTER LAB - 2") -> Image.Image:
    img, d, rng, horizon = _base(seed)
    _sign(d, 90, 70, sign)
    d.rectangle([W - 420, 60, W - 120, 250], fill=(245, 245, 245), outline=(120, 120, 120), width=4)  # whiteboard
    rows = 4
    per = [n_monitors // rows + (1 if i < n_monitors % rows else 0) for i in range(rows)]
    per = sorted(per)  # fewer at the back
    cells = list(_row_layout(rows, per, horizon))
    cur_row = -1
    for r, cx, y, s, cell_w in cells:
        if r != cur_row:
            cur_row = r
            span = W * (0.55 + 0.38 * ((r + 1) / rows)) + 30
            d.rectangle([(W - span) / 2, y, (W + span) / 2, y + int(26 * s)], fill=(168, 112, 62))  # desk top
            d.rectangle([(W - span) / 2, y + int(26 * s), (W + span) / 2, y + int(70 * s)], fill=(120, 84, 52))
        mw = min(cell_w * 0.72, 120 * s)
        mh = mw * 0.62
        x0, y1 = cx - mw / 2, y - 6 * s - 10 * s
        d.rectangle([cx - 4 * s, y1, cx + 4 * s, y], fill=(105, 105, 110))           # stand (mid grey)
        d.rectangle([x0, y1 - mh, x0 + mw, y1], fill=(22, 22, 26))                   # bezel
        bz = max(3, int(6 * s))
        scr = rng.choice([(170, 205, 235), (190, 220, 240), (160, 196, 228)])
        d.rectangle([x0 + bz, y1 - mh + bz, x0 + mw - bz, y1 - bz], fill=scr)       # screen
        d.rectangle([cx - 30 * s, y + 4 * s, cx + 30 * s, y + 12 * s], fill=(55, 55, 60))  # keyboard
        d.rectangle([cx - 22 * s, y + int(70 * s), cx + 22 * s, y + int(110 * s)], fill=(78, 78, 86))  # chair back
    return _finish(img, seed)


def scene_classroom(n_desks: int, seed: int, sign="CLASSROOM 204") -> Image.Image:
    img, d, rng, horizon = _base(seed, wall=(232, 228, 214))
    d.rectangle([W * 0.22, 70, W * 0.78, horizon - 50], fill=(28, 70, 48), outline=(120, 90, 60), width=8)  # board
    d.text((W * 0.26, 110), "Unit 3: Thermodynamics", font=pil_font(34), fill=(235, 235, 225))
    _sign(d, 40, 60, sign, size=26)
    rows = 5
    per = [n_desks // rows + (1 if i < n_desks % rows else 0) for i in range(rows)]
    for r, cx, y, s, cell_w in _row_layout(rows, per, horizon):
        bw = cell_w * 0.74
        d.rectangle([cx - bw / 2, y, cx + bw / 2, y + 24 * s], fill=(172, 110, 58))      # bench top
        d.rectangle([cx - bw / 2 + 4, y + 20 * s, cx - bw / 2 + 10 * s, y + 70 * s], fill=(60, 60, 64))  # legs
        d.rectangle([cx + bw / 2 - 10 * s, y + 20 * s, cx + bw / 2 - 4, y + 70 * s], fill=(60, 60, 64))
        d.rectangle([cx - bw / 2, y + 44 * s, cx + bw / 2, y + 52 * s], fill=(90, 90, 96))  # seat bar (grey)
    return _finish(img, seed)


def scene_library(n_shelves: int, seed: int, sign="CENTRAL LIBRARY") -> Image.Image:
    img, d, rng, horizon = _base(seed, wall=(230, 226, 216))
    _sign(d, W / 2 - 160, 40, sign)
    sw = (W - 120) / n_shelves
    for i in range(n_shelves):
        x0 = 60 + i * sw + 10
        x1 = x0 + sw - 20
        top, bot = 120, H - 120
        d.rectangle([x0, top, x1, bot], fill=(120, 80, 46))
        levels = 6
        lh = (bot - top) / levels
        for L in range(levels):
            yb = top + (L + 1) * lh
            d.rectangle([x0 + 8, yb - 10, x1 - 8, yb], fill=(176, 116, 62))  # shelf board
            x = x0 + 12
            while x < x1 - 20:
                bw = rng.randint(9, 16)
                bh = int(lh - 22 - rng.randint(0, 12))
                col = rng.choice([(170, 30, 40), (30, 70, 150), (30, 120, 70), (200, 150, 30), (110, 40, 120), (20, 110, 130)])
                d.rectangle([x, yb - 10 - bh, x + bw, yb - 11], fill=col)
                x += bw + 3
    return _finish(img, seed)


def scene_laboratory(n_benches: int, n_ext: int, seed: int, sign="ELECTRONICS LAB") -> Image.Image:
    img, d, rng, horizon = _base(seed, wall=(228, 230, 226))
    _sign(d, 70, 60, sign)
    for k in range(n_ext):
        x = W - 140 - k * 180
        d.rectangle([x, 300, x + 34, 400], fill=(200, 24, 28))      # extinguisher body
        d.rectangle([x + 10, 286, x + 24, 300], fill=(30, 30, 30))
    for b in range(n_benches):
        t = (b + 1) / n_benches
        s = 0.5 + 0.5 * t
        y = horizon + 40 + int((H - horizon - 160) * t)
        span = W * (0.5 + 0.4 * t)
        x0 = (W - span) / 2
        d.rectangle([x0, y, x0 + span, y + 28 * s], fill=(52, 54, 58))            # epoxy top
        d.rectangle([x0 + 10, y + 28 * s, x0 + span - 10, y + 110 * s], fill=(205, 205, 200))  # cabinets
        for i in range(6):  # equipment on bench
            ex = x0 + span * (i + 0.5) / 6
            d.rectangle([ex - 26 * s, y - 40 * s, ex + 26 * s, y - 2], fill=(214, 214, 220), outline=(90, 90, 96))
            d.rectangle([ex - 16 * s, y - 32 * s, ex + 4 * s, y - 18 * s], fill=(60, 140, 90))
    return _finish(img, seed)


def scene_ramp(seed: int, sign="RAMP 1:12  ->") -> Image.Image:
    img, d, rng, horizon = _base(seed, wall=(214, 206, 190), floor=(170, 166, 158))
    _sign(d, 80, 80, sign)
    d.rectangle([W - 220, 70, W - 120, 170], fill=(30, 80, 170))
    d.ellipse([W - 185, 85, W - 165, 105], fill=(255, 255, 255))
    d.line([(W - 175, 105), (W - 175, 140), (W - 145, 140)], fill=(255, 255, 255), width=8)
    # ramp surface and two handrails rising left->right (~1:12 in perspective)
    d.polygon([(100, H - 120), (W - 100, H - 330), (W - 100, H - 260), (100, H - 40)], fill=(150, 146, 140))
    for off in (0, 70):
        d.line([(100, H - 260 - off), (W - 100, H - 470 - off)], fill=(60, 60, 64), width=9)
        for x in range(140, W - 100, 210):
            yy = H - 260 - off - (x - 100) * (210 / (W - 200))
            d.line([(x, yy), (x, yy + 150)], fill=(80, 80, 84), width=6)
    return _finish(img, seed)
