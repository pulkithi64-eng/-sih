"""Infrastructure photo analysis (classroom / computer lab / library / laboratory / accessibility evidence).

analyse_infra(path, evidence_type, campus_gps=None, max_age_months=12, max_distance_km=1.0, ref_date=None) -> {
  evidenceType, method: "yolov8n" | "heuristic",
  detections: [{label, conf, bbox:[x0,y0,x1,y1]}],
  counts: {label: n}             e.g. computer_lab {monitors, computers}; classroom {desks, seatsEstimated, boards}
  quality: {blurScore (variance of Laplacian), brightness (0-255), width, height},
  exif: {takenAt, gps:{lat,lng}|None, device, software},
  flags: [{code, severity, reason, evidence}]
}

Object detection: Ultralytics YOLOv8n is used when the package AND weights are available (never auto-installed).
Otherwise a deterministic OpenCV heuristic runs and says so (method="heuristic", low confidence):
monitor-like framed rectangles, wood-toned desk tops, book-spine strips, bench tops, red extinguisher cylinders,
inclined handrail lines. It is an assistive estimate for the officer, not an inspection.
Duplicate / stock photo detection is done at application level with sha256 + pHash (see hashing.py).
"""
from __future__ import annotations

import importlib.util
import math
import os
from datetime import date, datetime
from pathlib import Path

import numpy as np
from PIL import Image

EDITORS = ("photoshop", "gimp", "lightroom", "snapseed", "picsart", "canva", "pixlr", "fotor", "paint")
TYPE_ALIASES = {
    "INFRA_PHOTO_CLASSROOM": "classroom", "INFRA_PHOTO_COMPUTER_LAB": "computer_lab",
    "INFRA_PHOTO_LIBRARY": "library", "INFRA_PHOTO_LABORATORY": "laboratory",
    "INFRA_PHOTO_ACCESSIBILITY": "accessibility",
}
_yolo = None
_yolo_failed = False


def _flag(code, severity, reason, **evidence):
    return {"code": code, "severity": severity, "reason": reason, "evidence": evidence}


# ----------------------------------------------------------------------------- EXIF
def _rat(v) -> float:
    try:
        return float(v[0]) / float(v[1]) if isinstance(v, tuple) else float(v)
    except (TypeError, ZeroDivisionError, IndexError):
        return 0.0


def _dms(vals, ref) -> float | None:
    try:
        d, m, s = (_rat(x) for x in vals)
    except (TypeError, ValueError):
        return None
    out = d + m / 60 + s / 3600
    return -out if str(ref).upper().startswith(("S", "W")) else out


def read_exif(img: Image.Image) -> dict:
    out = {"takenAt": None, "gps": None, "device": None, "software": None}
    try:
        ex = img.getexif()
    except Exception:
        return out
    if not ex:
        return out
    make, model = ex.get(271), ex.get(272)
    if make or model:
        out["device"] = " ".join(str(x).strip("\x00 ") for x in (make, model) if x)
    if ex.get(305):
        out["software"] = str(ex.get(305)).strip("\x00 ")
    try:
        sub = ex.get_ifd(0x8769)
        dto = sub.get(36867) or ex.get(306)
    except Exception:
        dto = ex.get(306)
    if dto:
        try:
            out["takenAt"] = datetime.strptime(str(dto).strip("\x00 "), "%Y:%m:%d %H:%M:%S").isoformat()
        except ValueError:
            out["takenAt"] = str(dto)
    try:
        gps = ex.get_ifd(0x8825)
        if gps and 2 in gps and 4 in gps:
            lat = _dms(gps[2], gps.get(1, "N"))
            lng = _dms(gps[4], gps.get(3, "E"))
            if lat is not None and lng is not None:
                out["gps"] = {"lat": round(lat, 6), "lng": round(lng, 6)}
    except Exception:
        pass
    return out


def haversine_km(a: dict, b: dict) -> float:
    r = 6371.0
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lng"], b["lat"], b["lng"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


# ----------------------------------------------------------------------------- detectors
def _try_yolo():
    global _yolo, _yolo_failed
    if _yolo is not None or _yolo_failed:
        return _yolo
    if os.environ.get("VERISENSE_INFRA_DETECTOR", "auto").lower() == "heuristic" or importlib.util.find_spec("ultralytics") is None:
        _yolo_failed = True
        return None
    try:
        from ultralytics import YOLO  # type: ignore

        _yolo = YOLO(os.environ.get("VERISENSE_YOLO_WEIGHTS", "yolov8n.pt"))
    except Exception:
        _yolo_failed = True
        _yolo = None
    return _yolo


COCO_MAP = {"tv": "monitor", "laptop": "monitor", "chair": "chair", "dining table": "desk", "bench": "desk",
            "book": "book", "keyboard": "keyboard", "person": "person", "potted plant": "plant"}


def _yolo_detect(model, img_bgr) -> list[dict]:
    res = model.predict(img_bgr, verbose=False, conf=0.25)[0]
    dets = []
    for b in res.boxes:
        name = res.names[int(b.cls)]
        label = COCO_MAP.get(name)
        if label:
            dets.append({"label": label, "conf": round(float(b.conf), 3),
                         "bbox": [round(float(v), 1) for v in b.xyxy[0].tolist()]})
    return dets


def _rect_contours(mask, min_area, max_area):
    import cv2

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        area = w * h
        if area < min_area or area > max_area:
            continue
        fill = cv2.contourArea(c) / max(area, 1)
        yield x, y, w, h, fill


def _detect_monitors(bgr) -> list[dict]:
    """Framed rectangles: a dark bezel enclosing a brighter, fairly uniform screen."""
    import cv2

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    H, W = gray.shape
    dark = (gray < 60).astype(np.uint8) * 255
    cnts, hier = cv2.findContours(dark, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    dets = []
    if hier is None:
        return dets
    hier = hier[0]
    for i, c in enumerate(cnts):
        if hier[i][3] != -1:      # only outer contours
            continue
        x, y, w, h = cv2.boundingRect(c)
        if w * h < W * H * 0.0006 or w * h > W * H * 0.08:
            continue
        ar = w / max(h, 1)
        if not 1.1 <= ar <= 2.4:
            continue
        child = hier[i][2]
        best_hole = 0
        while child != -1:
            best_hole = max(best_hole, cv2.contourArea(cnts[child]))
            child = hier[child][0]
        if best_hole < 0.45 * w * h:
            continue
        inner = gray[y + h // 5: y + h - h // 5, x + w // 5: x + w - w // 5]
        if inner.size == 0 or inner.mean() < 90 or inner.std() > 45:
            continue
        dets.append({"label": "monitor", "conf": 0.42, "bbox": [x, y, x + w, y + h]})
    return dets


def _hsv(bgr):
    import cv2

    return cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)


def _detect_desks(bgr) -> list[dict]:
    """Wood-toned wide horizontal slabs (desk / bench tops)."""
    import cv2

    hsv = _hsv(bgr)
    H, W = bgr.shape[:2]
    mask = cv2.inRange(hsv, (5, 80, 60), (22, 230, 210))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    dets = []
    for x, y, w, h, fill in _rect_contours(mask, W * H * 0.0004, W * H * 0.05):
        if w / max(h, 1) >= 2.3 and fill > 0.6:
            dets.append({"label": "desk", "conf": 0.38, "bbox": [x, y, x + w, y + h]})
    return dets


def _detect_boards(bgr) -> list[dict]:
    import cv2

    hsv = _hsv(bgr)
    H, W = bgr.shape[:2]
    green = cv2.inRange(hsv, (40, 40, 20), (90, 255, 110))
    dark = cv2.inRange(hsv, (0, 0, 0), (180, 80, 45))
    dets = []
    for m in (green, dark):
        for x, y, w, h, fill in _rect_contours(m, W * H * 0.04, W * H * 0.5):
            if w / max(h, 1) >= 1.6 and fill > 0.75 and y < H * 0.5:
                dets.append({"label": "board", "conf": 0.4, "bbox": [x, y, x + w, y + h]})
    return dets[:3]


def _detect_books(bgr) -> tuple[list[dict], list[dict]]:
    """Book spines = tall narrow saturated strips; bookcases = tall wood-toned frames."""
    import cv2

    hsv = _hsv(bgr)
    H, W = bgr.shape[:2]
    sat = cv2.inRange(hsv, (0, 90, 50), (180, 255, 255))
    wood = cv2.inRange(hsv, (5, 80, 60), (22, 230, 210))
    sat = cv2.bitwise_and(sat, cv2.bitwise_not(wood))
    books = []
    sat = cv2.erode(sat, np.ones((1, 2), np.uint8))
    for x, y, w, h, fill in _rect_contours(sat, W * H * 0.00008, W * H * 0.01):
        if h / max(w, 1) >= 2.2:
            books.append({"label": "book", "conf": 0.33, "bbox": [x, y, x + w, y + h]})
    cases = []
    for x, y, w, h, fill in _rect_contours(wood, W * H * 0.015, W * H * 0.5):
        if h / max(w, 1) >= 1.2:
            cases.append({"label": "bookcase", "conf": 0.35, "bbox": [x, y, x + w, y + h]})
    return books, cases


def _detect_lab(bgr) -> tuple[list[dict], list[dict]]:
    import cv2

    hsv = _hsv(bgr)
    H, W = bgr.shape[:2]
    bench = cv2.inRange(hsv, (0, 0, 38), (180, 45, 80))      # dark grey/black epoxy bench tops
    benches = []
    for x, y, w, h, fill in _rect_contours(bench, W * H * 0.006, W * H * 0.2):
        if w / max(h, 1) >= 3.0 and fill > 0.7:
            benches.append({"label": "workbench", "conf": 0.36, "bbox": [x, y, x + w, y + h]})
    red = cv2.bitwise_or(cv2.inRange(hsv, (0, 140, 90), (8, 255, 255)), cv2.inRange(hsv, (172, 140, 90), (180, 255, 255)))
    ext = []
    for x, y, w, h, fill in _rect_contours(red, W * H * 0.0006, W * H * 0.02):
        if 1.8 <= h / max(w, 1) <= 4.5:
            ext.append({"label": "fire_extinguisher", "conf": 0.35, "bbox": [x, y, x + w, y + h]})
    return benches, ext


def _detect_ramp(bgr) -> list[dict]:
    import cv2

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    H, W = gray.shape
    edges = cv2.Canny(gray, 60, 160)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 360, threshold=120, minLineLength=int(W * 0.35), maxLineGap=12)
    dets = []
    if lines is None:
        return dets
    for x1, y1, x2, y2 in lines.reshape(-1, 4):
        ang = abs(math.degrees(math.atan2(y2 - y1, x2 - x1)))
        ang = min(ang, 180 - ang)
        if 3 <= ang <= 25:
            dets.append({"label": "ramp_or_handrail", "conf": 0.3, "bbox": [int(min(x1, x2)), int(min(y1, y2)), int(max(x1, x2)), int(max(y1, y2))],
                         "angleDeg": round(ang, 1)})
    # merge near-parallel duplicates
    merged = []
    for d in sorted(dets, key=lambda d: d["bbox"][1]):
        if merged and abs(merged[-1]["bbox"][1] - d["bbox"][1]) < H * 0.03 and abs(merged[-1]["angleDeg"] - d["angleDeg"]) < 3:
            continue
        merged.append(d)
    return merged


def _heuristic(bgr, kind: str) -> tuple[list[dict], dict]:
    if kind == "computer_lab":
        m = _detect_monitors(bgr)
        return m, {"monitors": len(m), "computers": len(m)}
    if kind == "classroom":
        d, b = _detect_desks(bgr), _detect_boards(bgr)
        return d + b, {"desks": len(d), "seatsEstimated": 2 * len(d), "boards": len(b)}
    if kind == "library":
        books, shelves = _detect_books(bgr)
        return books + shelves, {"books": len(books), "bookcases": len(shelves)}
    if kind == "laboratory":
        benches, ext = _detect_lab(bgr)
        return benches + ext, {"workbenches": len(benches), "fireExtinguishers": len(ext)}
    if kind == "accessibility":
        r = _detect_ramp(bgr)
        return r, {"rampHandrails": len(r)}
    return [], {}


def _yolo_counts(dets, kind):
    c = {}
    for d in dets:
        c[d["label"]] = c.get(d["label"], 0) + 1
    if kind == "computer_lab":
        return {"monitors": c.get("monitor", 0), "computers": c.get("monitor", 0), "chairs": c.get("chair", 0)}
    if kind == "classroom":
        return {"desks": c.get("desk", 0), "chairs": c.get("chair", 0), "seatsEstimated": max(c.get("chair", 0), 2 * c.get("desk", 0))}
    if kind == "library":
        return {"books": c.get("book", 0)}
    return c


# ----------------------------------------------------------------------------- main
def analyse_infra(path: str | Path, evidence_type: str, campus_gps: dict | None = None, max_age_months: int = 12,
                  max_distance_km: float = 1.0, ref_date: date | None = None) -> dict:
    import cv2

    path = Path(path)
    kind = TYPE_ALIASES.get(evidence_type, evidence_type).lower()
    ref_date = ref_date or date.today()
    img = Image.open(path)
    exif = read_exif(img)
    bgr = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    H, W = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    g = cv2.resize(gray, (1024, int(1024 * H / W))) if W > 1024 else gray
    blur = float(cv2.Laplacian(g, cv2.CV_64F).var())
    bright = float(gray.mean())
    quality = {"blurScore": round(blur, 1), "brightness": round(bright, 1), "width": W, "height": H}

    method = "heuristic"
    model = _try_yolo()
    if model is not None:
        try:
            dets = _yolo_detect(model, bgr)
            counts = _yolo_counts(dets, kind)
            method = "yolov8n"
        except Exception:
            dets, counts = _heuristic(bgr, kind)
    else:
        dets, counts = _heuristic(bgr, kind)

    flags = []
    if blur < 60:
        flags.append(_flag("LOW_QUALITY_BLUR", "MINOR", f"Photo is blurred (Laplacian variance {blur:.0f} < 60); objects cannot be reliably counted", metric=round(blur, 1)))
    if bright < 50 or bright > 225:
        flags.append(_flag("POOR_LIGHTING", "MINOR", f"Photo brightness {bright:.0f}/255 is outside the usable range", metric=round(bright, 1)))
    if min(W, H) < 480:
        flags.append(_flag("LOW_RESOLUTION", "MINOR", f"Photo resolution {W}x{H} is too low for evidence", metric=f"{W}x{H}"))
    if not exif["takenAt"] and not exif["gps"]:
        flags.append(_flag("EXIF_MISSING", "MINOR", "No capture date or GPS in EXIF - cannot confirm when/where the photo was taken (metadata stripped or re-saved)"))
    else:
        if exif["takenAt"]:
            try:
                taken = datetime.fromisoformat(exif["takenAt"]).date()
                age_m = (ref_date.year - taken.year) * 12 + (ref_date.month - taken.month)
                if taken > ref_date:
                    flags.append(_flag("PHOTO_DATE_IN_FUTURE", "MINOR", f"EXIF capture date {taken} is after the submission date", takenAt=exif["takenAt"]))
                elif age_m > max_age_months:
                    flags.append(_flag("PHOTO_TOO_OLD", "MAJOR", f"Photo taken {taken} ({age_m} months ago) - older than the {max_age_months}-month evidence window",
                                       takenAt=exif["takenAt"], ageMonths=age_m))
            except ValueError:
                pass
        if not exif["gps"]:
            flags.append(_flag("GPS_MISSING", "MINOR", "Photo is not geo-tagged; location cannot be matched to the campus"))
        elif campus_gps and campus_gps.get("lat") is not None:
            dist = haversine_km(exif["gps"], campus_gps)
            if dist > max_distance_km:
                flags.append(_flag("GPS_FAR_FROM_CAMPUS", "MAJOR",
                                   f"Photo geo-tag ({exif['gps']['lat']:.4f}, {exif['gps']['lng']:.4f}) is {dist:.1f} km from the registered campus location",
                                   distanceKm=round(dist, 2), photoGps=exif["gps"], campusGps=campus_gps))
    if exif.get("software") and any(e in exif["software"].lower() for e in EDITORS):
        flags.append(_flag("PHOTO_EDITED", "MAJOR", f"EXIF Software '{exif['software']}' indicates the photo was edited", software=exif["software"]))
    if counts and not any(v for k, v in counts.items() if k != "seatsEstimated"):
        flags.append(_flag("EXPECTED_OBJECTS_NOT_DETECTED", "MINOR", f"No {kind.replace('_', ' ')} objects detected ({method}); photo may not show the declared facility"))

    return {"evidenceType": evidence_type, "kind": kind, "method": method,
            "methodNote": "Ultralytics YOLOv8n (COCO classes)" if method == "yolov8n" else
                          "OpenCV shape/colour heuristic - low-confidence estimate; officer should confirm counts",
            "detections": dets[:300], "counts": counts, "quality": quality, "exif": exif, "flags": flags}
