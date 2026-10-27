"""Document forensics - PRELIMINARY tamper indicators (never proof of forgery).

analyse(path, out_dir=None) -> {
  elaScore:        0..100 localised error-level contrast (0 = uniform; >= 35 = localised anomaly) or None
  elaHeatmapPath:  PNG (amplified ELA, flagged regions boxed) written next to the file (or in out_dir), or None
  metadata:        {format, producer, creator, created, modified, software, revisions, pages, ...}
  flags:           [{code, severity, reason, evidence{page, bbox, excerpt, ...}}]
}

Checks
* Error Level Analysis (JPEG resave at q=90, abs diff). Block ELA is normalised by local edge energy so that
  ordinary text strokes do not dominate; spatially clustered blocks with unusually high ratio are reported with a
  bbox. Run on JPG/PNG uploads and on raster images embedded in PDFs (scanned pages).
* PDF metadata: Producer/Creator naming image/PDF editors, ModDate != CreationDate, incremental updates
  (multiple %%EOF / startxref sections), digital signature presence.
* PDF text layer: a rarely used font family inside a single line ("font inconsistency near 'value'"),
  overlapping text spans with different content (text pasted over text).
* EXIF: Software tag naming an editor, DateTime (modified) differing from DateTimeOriginal.
"""
from __future__ import annotations

import io
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
ELA_QUALITY = 90
BLOCK = 16
RATIO_FLOOR = 0.28        # absolute minimum normalised ELA for a suspicious block
RATIO_REL = 4.0           # ... and this many times the image's own 99th percentile
MIN_REGION_BLOCKS = 3

EDITOR_MAJOR = re.compile(
    r"photoshop|gimp|canva|pdfescape|sejda|pdf-?xchange\s+editor|foxit\s+(phantom|pdf\s*editor)|nitro\s*pro|"
    r"pdf\s*editor|pixlr|paint\.net|inkscape|affinity|corel|picsart|snapseed|fotor|smallpdf\s+edit|pdffiller|"
    r"pdfelement|wondershare|master\s*pdf\s*editor|pdf\s*candy", re.I)
EDITOR_MINOR = re.compile(r"ilovepdf|smallpdf|pdf24|online2pdf|soda\s*pdf", re.I)

DISCLAIMER = "preliminary indicator - requires officer review; not proof of tampering"


def _flag(code, severity, reason, **evidence):
    return {"code": code, "severity": severity, "reason": f"{reason} ({DISCLAIMER})", "evidence": evidence}


# ----------------------------------------------------------------------------- ELA
def _jpeg_roundtrip(img: Image.Image, q: int) -> Image.Image:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=q)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def ela_map(img: Image.Image, quality: int = ELA_QUALITY) -> np.ndarray:
    img = img.convert("RGB")
    a = np.asarray(img, dtype=np.int16)
    b = np.asarray(_jpeg_roundtrip(img, quality), dtype=np.int16)
    return np.abs(a - b).max(axis=2).astype(np.float32)


def _block_mean(a: np.ndarray, bs: int = BLOCK) -> np.ndarray:
    h, w = a.shape[:2]
    a = a[: h // bs * bs, : w // bs * bs]
    return a.reshape(h // bs, bs, w // bs, bs).mean(axis=(1, 3))


def ela_regions(img: Image.Image) -> dict:
    """Return {score, ratioMap, ela, regions:[{bbox(px), meanRatio, blocks}], baseline}."""
    import cv2

    img = img.convert("RGB")
    if max(img.size) > 2600:
        k = 2600 / max(img.size)
        img = img.resize((int(img.width * k), int(img.height * k)), Image.LANCZOS)
    ela = ela_map(img)
    gray = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2GRAY).astype(np.float32)
    lap = np.abs(cv2.Laplacian(gray, cv2.CV_32F))
    be, bg = _block_mean(ela), _block_mean(lap)
    ratio = be / (bg + 1.0)
    if ratio.size == 0:
        return {"score": 0.0, "regions": [], "ela": ela, "baseline": 0.0, "size": img.size}
    baseline = float(np.percentile(ratio, 99))
    thr = max(RATIO_FLOOR, RATIO_REL * baseline)
    mask = (ratio > thr) & (be > 1.5)
    regions = []
    if mask.any():
        m8 = cv2.dilate(mask.astype(np.uint8), np.ones((3, 3), np.uint8))
        n, labels, stats, _ = cv2.connectedComponentsWithStats(m8, connectivity=8)
        for i in range(1, n):
            comp = (labels == i) & mask
            cnt = int(comp.sum())
            if cnt < MIN_REGION_BLOCKS:
                continue
            x, y, w, h = stats[i][:4]
            regions.append({"bbox": [int(x * BLOCK), int(y * BLOCK), int((x + w) * BLOCK), int((y + h) * BLOCK)],
                            "meanRatio": round(float(ratio[comp].mean()), 3), "blocks": cnt})
    regions.sort(key=lambda r: r["meanRatio"] * r["blocks"], reverse=True)
    peak = max((r["meanRatio"] for r in regions), default=float(ratio.max()))
    score = 0.0 if not regions else min(100.0, 100.0 * (peak - baseline) / 0.6)
    return {"score": round(max(score, 0.0), 1), "regions": regions[:8], "ela": ela, "baseline": round(baseline, 4), "size": img.size}


def write_heatmap(ela: np.ndarray, regions: list[dict], out_path: Path) -> str:
    import cv2

    amp = np.clip(ela * (255.0 / max(8.0, float(np.percentile(ela, 99.9)))), 0, 255).astype(np.uint8)
    heat = cv2.applyColorMap(amp, cv2.COLORMAP_INFERNO)
    for r in regions:
        x0, y0, x1, y1 = r["bbox"]
        cv2.rectangle(heat, (x0, y0), (x1, y1), (80, 255, 80), 2)
    if max(heat.shape[:2]) > 1600:
        k = 1600 / max(heat.shape[:2])
        heat = cv2.resize(heat, (int(heat.shape[1] * k), int(heat.shape[0] * k)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".png", heat)
    out_path.write_bytes(buf.tobytes())
    return str(out_path)


# ----------------------------------------------------------------------------- EXIF
def image_exif(img: Image.Image) -> dict:
    out = {}
    try:
        ex = img.getexif()
    except Exception:
        return out
    if not ex:
        return out
    tags = {305: "software", 306: "modified", 271: "make", 272: "model"}
    for k, name in tags.items():
        if ex.get(k):
            out[name] = str(ex.get(k)).strip("\x00 ")
    try:
        sub = ex.get_ifd(0x8769)
        if sub.get(36867):
            out["created"] = str(sub.get(36867)).strip("\x00 ")
    except Exception:
        pass
    return out


def _exif_flags(meta: dict) -> list[dict]:
    flags = []
    sw = meta.get("software") or ""
    if EDITOR_MAJOR.search(sw):
        flags.append(_flag("IMAGE_EDITING_SOFTWARE", "MAJOR", f"EXIF Software tag names an image editor: '{sw}'",
                           excerpt=sw, field="EXIF:Software"))
    c, m = meta.get("created"), meta.get("modified")
    if c and m and c != m:
        flags.append(_flag("IMAGE_MODIFIED_AFTER_CAPTURE", "MINOR",
                           f"EXIF DateTime ({m}) differs from DateTimeOriginal ({c}) - image re-saved after capture",
                           excerpt=f"{c} -> {m}", field="EXIF:DateTime"))
    return flags


# ----------------------------------------------------------------------------- PDF
def _pdf_date(s: str | None) -> str | None:
    if not s:
        return None
    m = re.match(r"D?:?(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?", s)
    if not m:
        return s
    parts = [int(p) if p else d for p, d in zip(m.groups(), (0, 1, 1, 0, 0, 0))]
    try:
        return datetime(*parts).isoformat()
    except ValueError:
        return s


def _font_family(name: str) -> str:
    name = name.split("+", 1)[-1]
    name = re.split(r"[-,]", name)[0]
    name = re.sub(r"(?i)(bold|italic|oblique|regular|roman|mt|ps|light|medium|semibold|black|condensed)+$", "", name)
    return name.strip().lower() or "unknown"


def _pdf_structure(raw: bytes) -> dict:
    eofs = len(re.findall(rb"%%EOF", raw))
    startxrefs = len(re.findall(rb"startxref", raw))
    linearized = b"/Linearized" in raw[:2048]
    signed = b"/ByteRange" in raw
    revisions = max(eofs, startxrefs)
    if linearized and revisions == 2:
        revisions = 1
    return {"revisions": revisions, "linearized": linearized, "digitallySigned": signed}


def _text_layer_flags(doc) -> list[dict]:
    flags = []
    fam_chars: Counter = Counter()
    pages_spans = []
    for pno, page in enumerate(doc, start=1):
        d = page.get_text("dict")
        lines = []
        for blk in d.get("blocks", []):
            if blk.get("type") != 0:
                continue
            for ln in blk.get("lines", []):
                spans = [s for s in ln.get("spans", []) if s.get("text", "").strip()]
                for s in spans:
                    s["_direction"] = ln.get("dir", (1.0, 0.0))
                for s in spans:
                    fam_chars[_font_family(s.get("font", ""))] += len(s["text"].strip())
                if spans:
                    lines.append(spans)
        pages_spans.append((pno, lines))
    total = sum(fam_chars.values()) or 1

    for pno, lines in pages_spans:
        # merge lines that share a baseline (PyMuPDF splits separately-drawn text objects into lines)
        rows: list[list[dict]] = []
        for spans in sorted(lines, key=lambda sp: round(sp[0]["bbox"][3], 0)):
            y = spans[0]["bbox"][3]
            if rows and abs(rows[-1][0]["bbox"][3] - y) < 2.5:
                rows[-1].extend(spans)
            else:
                rows.append(list(spans))
        for row in rows:
            fams = {_font_family(s.get("font", "")) for s in row}
            if len(fams) < 2:
                continue
            for s in row:
                fam = _font_family(s.get("font", ""))
                share = fam_chars[fam] / total
                others = {_font_family(o.get("font", "")) for o in row if o is not s}
                if share < 0.05 and fam not in others and len(s["text"].strip()) >= 2:
                    context = " ".join(o["text"].strip() for o in row)[:120]
                    flags.append(_flag(
                        "FONT_INCONSISTENCY", "MAJOR",
                        f"Font inconsistency near '{s['text'].strip()[:40]}': rendered in '{s.get('font')}' "
                        f"while the rest of the line uses {', '.join(sorted(others))} (this font covers {share:.1%} of the document text)",
                        page=pno, bbox=[round(v, 1) for v in s["bbox"]], excerpt=s["text"].strip()[:80],
                        font=s.get("font"), lineText=context))
        # overlapping spans with different content (text drawn over text)
        flat = [s for row in rows for s in row]
        for i in range(len(flat)):
            a = flat[i]
            for j in range(i + 1, len(flat)):
                b = flat[j]
                # Axis-aligned boxes overlap on adjacent rotated seal text.
                # Compare actual text quads in their shared baseline coordinates.
                direction = a["_direction"]
                other = b["_direction"]
                if direction[0] * other[0] + direction[1] * other[1] < 0.98:
                    continue
                import pymupdf

                def bounds(span):
                    quad = pymupdf.recover_quad(span["_direction"], span)
                    along = [p.x * direction[0] + p.y * direction[1] for p in quad]
                    across = [-p.x * direction[1] + p.y * direction[0] for p in quad]
                    return min(along), min(across), max(along), max(across)

                ax0, ay0, ax1, ay1 = bounds(a)
                bx0, by0, bx1, by1 = bounds(b)
                iw = min(ax1, bx1) - max(ax0, bx0)
                ih = min(ay1, by1) - max(ay0, by0)
                if iw <= 0 or ih <= 0:
                    continue
                inter = iw * ih
                small = min((ax1 - ax0) * (ay1 - ay0), (bx1 - bx0) * (by1 - by0)) or 1
                if inter / small > 0.5 and a["text"].strip() != b["text"].strip():
                    flags.append(_flag("TEXT_OVERLAY", "MAJOR",
                                       f"Two different text runs occupy the same position ('{a['text'].strip()[:30]}' / '{b['text'].strip()[:30]}') - text may have been pasted over original content",
                                       page=pno, bbox=[round(min(a['bbox'][0], b['bbox'][0]), 1), round(min(a['bbox'][1], b['bbox'][1]), 1), round(max(a['bbox'][2], b['bbox'][2]), 1), round(max(a['bbox'][3], b['bbox'][3]), 1)],
                                       excerpt=f"{a['text'].strip()[:40]} | {b['text'].strip()[:40]}"))
    # de-duplicate (one flag per excerpt+page)
    seen, out = set(), []
    for f in flags:
        key = (f["code"], f["evidence"].get("page"), f["evidence"].get("excerpt"))
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out[:12]


def _analyse_pdf(path: Path, out_dir: Path | None) -> dict:
    import pymupdf

    raw = path.read_bytes()
    flags: list[dict] = []
    struct = _pdf_structure(raw)
    with pymupdf.open(path) as doc:
        md = doc.metadata or {}
        meta = {"format": "PDF", "producer": md.get("producer") or None, "creator": md.get("creator") or None,
                "created": _pdf_date(md.get("creationDate")), "modified": _pdf_date(md.get("modDate")),
                "software": None, "pages": doc.page_count, **struct}
        for key in ("producer", "creator"):
            val = meta.get(key) or ""
            if EDITOR_MAJOR.search(val):
                flags.append(_flag("PDF_EDITING_SOFTWARE", "MAJOR",
                                   f"PDF {key.title()} '{val}' is an image/PDF editing tool, not an issuing system",
                                   field=f"PDF:{key.title()}", excerpt=val))
            elif EDITOR_MINOR.search(val):
                flags.append(_flag("PDF_EDITING_SOFTWARE", "MINOR",
                                   f"PDF {key.title()} '{val}' indicates processing by an online PDF tool",
                                   field=f"PDF:{key.title()}", excerpt=val))
        c, m = meta["created"], meta["modified"]
        if c and m and c[:19] != m[:19]:
            try:
                delta = abs((datetime.fromisoformat(m[:19]) - datetime.fromisoformat(c[:19])).total_seconds())
            except ValueError:
                delta = 9e9
            if delta > 60:
                flags.append(_flag("PDF_MODIFIED_AFTER_CREATION", "MINOR",
                                   f"ModDate ({m}) differs from CreationDate ({c}) by {delta / 86400:.1f} days",
                                   field="PDF:ModDate", excerpt=f"{c} -> {m}"))
        if struct["revisions"] > 1:
            sev = "MINOR" if struct["digitallySigned"] else "MAJOR"
            note = " (document carries a digital signature; signed revisions are normal)" if struct["digitallySigned"] else ""
            flags.append(_flag("PDF_INCREMENTAL_UPDATE", sev,
                               f"PDF has {struct['revisions']} revisions (incremental updates appended after the original save){note}",
                               field="PDF:xref", excerpt=f"%%EOF x{struct['revisions']}"))
        flags.extend(_text_layer_flags(doc))

        # ELA on embedded raster images (scanned pages / pasted images)
        best = None
        for pno, page in enumerate(doc, start=1):
            if pno > 3:
                break
            for info in page.get_images(full=True):
                xref = info[0]
                try:
                    ext = doc.extract_image(xref)
                except Exception:
                    continue
                if not ext or ext.get("width", 0) < 300 or ext.get("height", 0) < 300:
                    continue
                img = Image.open(io.BytesIO(ext["image"]))
                res = ela_regions(img)
                rects = page.get_image_rects(xref)
                rect = rects[0] if rects else page.rect
                sx, sy = rect.width / res["size"][0], rect.height / res["size"][1]
                for r in res["regions"][:3]:
                    x0, y0, x1, y1 = r["bbox"]
                    flags.append(_flag("ELA_LOCALISED_ANOMALY", "MAJOR",
                                       f"Embedded scan on page {pno} has a localised region whose JPEG error level is "
                                       f"{r['meanRatio'] / max(res['baseline'], 1e-3):.1f}x the page norm - consistent with pasted/edited content",
                                       page=pno, bbox=[round(rect.x0 + x0 * sx, 1), round(rect.y0 + y0 * sy, 1),
                                                       round(rect.x0 + x1 * sx, 1), round(rect.y0 + y1 * sy, 1)],
                                       elaRatio=r["meanRatio"], baseline=res["baseline"]))
                if best is None or res["score"] > best["score"]:
                    best = res
        heat_path = None
        if best is None:  # born-digital page: render for an informational heatmap only
            pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)) if doc.page_count else None
            if pix is not None:
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                ela = ela_map(img)
                best = {"score": None, "regions": [], "ela": ela}
        if best is not None:
            heat_path = write_heatmap(best["ela"], best["regions"], _heat_path(path, out_dir))
    return {"elaScore": best["score"] if best else None, "elaHeatmapPath": heat_path, "metadata": meta, "flags": flags}


def _heat_path(path: Path, out_dir: Path | None) -> Path:
    d = Path(out_dir) if out_dir else path.parent
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{path.name}.ela.png"


def _analyse_image(path: Path, out_dir: Path | None) -> dict:
    img = Image.open(path)
    exif = image_exif(img)
    meta = {"format": (img.format or path.suffix.lstrip(".")).upper(), "producer": None, "creator": None,
            "created": exif.get("created"), "modified": exif.get("modified"), "software": exif.get("software"),
            "make": exif.get("make"), "model": exif.get("model"), "width": img.width, "height": img.height}
    flags = _exif_flags(exif)
    res = ela_regions(img)
    sx = img.width / res["size"][0]
    sy = img.height / res["size"][1]
    for r in res["regions"][:3]:
        x0, y0, x1, y1 = r["bbox"]
        flags.append(_flag("ELA_LOCALISED_ANOMALY", "MAJOR",
                           f"Localised region with JPEG error level {r['meanRatio'] / max(res['baseline'], 1e-3):.1f}x the image norm - "
                           f"consistent with pasted or re-touched content",
                           page=1, bbox=[round(x0 * sx), round(y0 * sy), round(x1 * sx), round(y1 * sy)],
                           elaRatio=r["meanRatio"], baseline=res["baseline"]))
    heat = write_heatmap(res["ela"], res["regions"], _heat_path(path, out_dir))
    return {"elaScore": res["score"], "elaHeatmapPath": heat, "metadata": meta, "flags": flags}


def analyse(path: str | Path, out_dir: str | Path | None = None) -> dict:
    path = Path(path)
    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            return _analyse_pdf(path, Path(out_dir) if out_dir else None)
        if ext in IMAGE_EXT:
            return _analyse_image(path, Path(out_dir) if out_dir else None)
    except Exception as exc:  # corrupt/unsupported file: report, do not crash the pipeline
        return {"elaScore": None, "elaHeatmapPath": None, "metadata": {"format": ext.lstrip(".").upper()},
                "flags": [_flag("FILE_UNREADABLE", "MINOR", f"File could not be fully parsed for forensics: {exc}")]}
    return {"elaScore": None, "elaHeatmapPath": None, "metadata": {"format": ext.lstrip(".").upper() or "UNKNOWN"}, "flags": []}
