"""Explainable document-type classifier: weighted keyword / regex evidence per docType + filename hints.

classify(text, filename) -> {docType, confidence (0..1), signals: [human-readable reasons], scores: {docType: score}}

Every pattern contributes its weight at most once (so long documents do not dominate); the confidence
combines evidence strength (saturating) with the margin over the runner-up type.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp", ".heic"}
PAN_RE = re.compile(r"\b[A-Z]{3}[PCHFATBLJG][A-Z]\d{4}[A-Z]\b")

# (regex, weight, label) per docType. Real-world phrasing plus generic terms - not tuned to one template.
P = re.IGNORECASE
RULES: dict[str, list[tuple[str, float, str]]] = {
    "SOCIETY_TRUST_REGISTRATION": [
        (r"societies registration act", 6, "Societies Registration Act"),
        (r"(public )?trusts? act|trust deed|deed of trust", 4, "Trust Act / trust deed"),
        (r"registrar of (societies|public trusts)|charity commissioner", 5, "Registrar of Societies / Charity Commissioner"),
        (r"certificate of registration|registration certificate", 3, "registration certificate wording"),
        (r"memorandum of association|rules and regulations of the society", 3, "memorandum of association"),
        (r"\bsociety\b|\btrust\b|\bmandal\b", 1, "society/trust term"),
        (r"change (in|of) (the )?name", 1, "change of name"),
        (r"resolution", 1, "resolution"),
    ],
    "LAND_DOCUMENT": [
        (r"sale deed|conveyance deed|lease deed|gift deed|deed of (sale|conveyance|lease)", 6, "deed of sale/lease"),
        (r"survey no|gat no|khasra|khata|plot no|s\.\s?no\.", 3, "survey / khasra / plot number"),
        (r"7\s?/\s?12|satbara|record of rights|jamabandi|mutation (entry|extract)|land record", 4, "record-of-rights / mutation"),
        (r"sub[- ]?registrar", 3, "Sub-Registrar"),
        (r"\b(acres?|hectares?|guntha|bigha)\b", 2, "land area unit"),
        (r"\b(vendor|vendee|purchaser|lessor|lessee|occupant|khatedar)\b", 2, "transacting parties"),
        (r"revenue (department|village)|tehsil|taluka|patwari|talathi", 2, "revenue administration"),
    ],
    "BUILDING_PLAN_APPROVAL": [
        (r"building plan|sanctioned plan|layout (plan )?approval|building permission|approval of (the )?building plans?", 6, "building plan approval"),
        (r"commencement certificate", 4, "commencement certificate"),
        (r"town planning|development control|development authority|building permission cell", 2, "planning authority"),
        (r"\bF\.?S\.?I\b|floor space index|setback", 2, "FSI / setbacks"),
        (r"permit no|permission no|plan approval no", 2, "permit number"),
        (r"proposed construction|sanctioned built[- ]?up", 2, "sanctioned construction"),
    ],
    "OCCUPANCY_CERTIFICATE": [
        (r"occupancy certificate|occupation certificate|completion certificate|building completion", 7, "occupancy / completion certificate"),
        (r"fit for (occupation|occupancy|use)|permitted to (occupy|use)|permission to occupy", 3, "fit for occupation"),
        (r"completed in accordance with|as per (the )?sanctioned plan", 2, "completed per sanctioned plan"),
    ],
    "FIRE_NOC": [
        (r"\bfire\b", 2, "'fire'"),
        (r"fire (safety|&|and) ?(emergency)?|fire services|fire brigade|fire department", 4, "fire services authority"),
        (r"fire (noc|no objection)|fire safety certificate|no objection certificate .{0,40}fire", 6, "Fire NOC wording"),
        (r"chief fire officer|divisional fire officer|fire officer", 3, "Fire Officer signatory"),
        (r"(fire )?(extinguishers?|hydrants?|sprinklers?|fire alarm)", 2, "fire-fighting installations"),
        (r"no objection certificate", 1, "'No Objection Certificate'"),
    ],
    "STRUCTURAL_STABILITY_CERT": [
        (r"structural(ly)? (stability|stable)", 7, "structural stability"),
        (r"structural (engineer|consultant)", 3, "structural engineer"),
        (r"structurally (safe|sound)|safe for (occupation|use)", 3, "structurally safe"),
        (r"\bR\.?C\.?C\.?\b|load[- ]bearing|foundation|seismic zone|IS ?456|IS ?1893", 2, "structural design terms"),
    ],
    "AFFIDAVIT_UNDERTAKING": [
        (r"\baffidavit\b", 6, "'Affidavit'"),
        (r"\bundertaking\b", 3, "'Undertaking'"),
        (r"solemnly (affirm|declare)|do hereby (state|declare|undertake|affirm)", 3, "solemn affirmation"),
        (r"\bnotar(y|ised|ized)\b|before me", 3, "notarisation"),
        (r"\bdeponent\b", 4, "'Deponent'"),
        (r"stamp paper|e-?stamp|non[- ]judicial", 3, "stamp paper"),
    ],
    "UNIVERSITY_AFFILIATION": [
        (r"\baffiliation\b", 4, "'Affiliation'"),
        (r"(grant|continuation|extension) of (provisional |permanent )?affiliation|(provisional|permanent|temporary) affiliation", 6, "grant/continuation of affiliation"),
        (r"\buniversity\b", 2, "'University'"),
        (r"consent of (the )?university|university (consent|no objection)|academic council|executive council", 3, "university consent / council"),
        (r"affiliated (college|institute)", 2, "affiliated college"),
    ],
    "STATE_GOVT_NOC": [
        (r"government of [A-Z][a-z]+|state government|govt\. of", 3, "State Government"),
        (r"directorate of technical education|department of (higher (and|&) )?technical education|commissionerate of technical education|technical education department", 5, "State technical education department"),
        (r"no objection certificate|\bNOC\b", 2, "NOC wording"),
        (r"government resolution|\bG\.R\.|essentiality certificate", 2, "Government resolution"),
    ],
    "PREVIOUS_EOA_LETTER": [
        (r"extension of approval", 7, "'Extension of Approval'"),
        (r"all india council for technical education|\bAICTE\b", 3, "AICTE"),
        (r"approval process handbook", 3, "Approval Process Handbook"),
        (r"\bF\.\s?No\.", 1, "F.No. file reference"),
        (r"permanent id", 2, "Permanent ID"),
        (r"\bEoA\b|letter of approval|approved intake", 2, "EoA / approved intake"),
    ],
    "NBA_ACCREDITATION": [
        (r"national board of accreditation|accreditation board for engineering", 6, "programme accreditation board"),
        (r"\bNBA\b", 3, "'NBA'"),
        (r"programme accreditation|accredited programme|accreditation (of|to) the (following )?programme|programmes? accredited", 4, "programme accreditation"),
        (r"tier[- ]?(i|ii|1|2)\b", 3, "Tier I/II"),
        (r"outcome[- ]based", 2, "outcome-based accreditation"),
        (r"\baccredit(ed|ation)\b", 2, "'accredited'"),
    ],
    "NAAC_ACCREDITATION": [
        (r"national assessment (and|&) accreditation council|\bNAAC\b", 7, "NAAC"),
        (r"\bCGPA\b", 4, "CGPA"),
        (r"institutional (accreditation|assessment)|assessment (and|&) accreditation", 4, "institutional assessment"),
        (r"\bgrade\b\s*['\"]?[AB]\+{0,2}", 2, "grade A/B"),
        (r"\bcycle\b", 2, "accreditation cycle"),
    ],
    "TER_PAYMENT_RECEIPT": [
        (r"payment receipt|e-?receipt|transaction receipt|payment acknowledg", 4, "payment receipt"),
        (r"transaction (id|no|reference)|\bTxn\b|\bUTR\b|bank ref", 4, "transaction id"),
        (r"\bTER\b|total expenditure recovery|processing fee", 5, "TER / processing fee"),
        (r"payment gateway|net ?banking|\bUPI\b|debit card|credit card", 2, "payment gateway"),
        (r"amount (paid|received)|\bamount\b", 1, "amount"),
    ],
    "FACULTY_ROSTER": [
        (r"faculty (list|roster|details|position|members)|list of (teaching )?faculty|teaching staff", 6, "faculty list heading"),
        (r"\bdesignation\b", 2, "designation column"),
        (r"assistant professor", 2, "Assistant Professor"),
        (r"associate professor", 2, "Associate Professor"),
        (r"date of joining|\bDOJ\b|joining date", 2, "date of joining column"),
        (r"\bqualification\b|ph\.?\s?d|m\.?\s?tech", 1, "qualification"),
        (r"\bPAN\b", 2, "PAN column"),
    ],
    "AUDITED_FINANCIAL_STATEMENT": [
        (r"balance sheet", 4, "balance sheet"),
        (r"income (and|&) expenditure|receipts (and|&) payments", 4, "income & expenditure"),
        (r"\bUDIN\b", 4, "UDIN"),
        (r"chartered accountants?", 3, "Chartered Accountants"),
        (r"auditor'?s'? report|independent auditor|audited (accounts|financial)", 4, "auditor's report"),
        (r"financial year|\bF\.?Y\.?\s?20\d\d", 1, "financial year"),
    ],
    "CORPUS_FUND_FDR": [
        (r"fixed deposit|term deposit|\bFDR\b|deposit receipt", 6, "fixed deposit receipt"),
        (r"corpus fund|endowment", 4, "corpus fund"),
        (r"maturity (date|value|amount)", 3, "maturity date/value"),
        (r"rate of interest|interest rate|\bp\.a\.", 2, "interest rate"),
        (r"\blien\b|jointly (held|with)", 2, "lien / joint holding"),
    ],
    "FLOOR_PLAN": [
        (r"floor plan|area statement|built[- ]?up area statement", 6, "floor plan / area statement"),
        (r"carpet area", 3, "carpet area"),
        (r"ground floor|first floor|second floor|third floor", 2, "floor-wise listing"),
        (r"\barchitect\b|council of architecture", 2, "architect"),
        (r"(class ?room|tutorial room|drawing hall|seminar hall|laboratory)\s.{0,30}\d+(\.\d+)?\s?(sq\.? ?m|m2|m²)", 3, "room-wise areas"),
    ],
}

# filename hints (lower-case substring) -> docType, weight
FILENAME_HINTS: list[tuple[str, str]] = [
    ("fire", "FIRE_NOC"), ("noc_fire", "FIRE_NOC"),
    ("land", "LAND_DOCUMENT"), ("deed", "LAND_DOCUMENT"), ("7_12", "LAND_DOCUMENT"), ("mutation", "LAND_DOCUMENT"),
    ("building_plan", "BUILDING_PLAN_APPROVAL"), ("plan_approval", "BUILDING_PLAN_APPROVAL"),
    ("occupancy", "OCCUPANCY_CERTIFICATE"), ("completion", "OCCUPANCY_CERTIFICATE"),
    ("structural", "STRUCTURAL_STABILITY_CERT"), ("stability", "STRUCTURAL_STABILITY_CERT"),
    ("affidavit", "AFFIDAVIT_UNDERTAKING"), ("undertaking", "AFFIDAVIT_UNDERTAKING"),
    ("affiliation", "UNIVERSITY_AFFILIATION"), ("university", "UNIVERSITY_AFFILIATION"),
    ("state_noc", "STATE_GOVT_NOC"), ("govt_noc", "STATE_GOVT_NOC"), ("dte", "STATE_GOVT_NOC"),
    ("eoa", "PREVIOUS_EOA_LETTER"), ("approval_letter", "PREVIOUS_EOA_LETTER"),
    ("nba", "NBA_ACCREDITATION"), ("naac", "NAAC_ACCREDITATION"),
    ("ter", "TER_PAYMENT_RECEIPT"), ("payment", "TER_PAYMENT_RECEIPT"), ("receipt", "TER_PAYMENT_RECEIPT"),
    ("faculty", "FACULTY_ROSTER"), ("roster", "FACULTY_ROSTER"),
    ("audit", "AUDITED_FINANCIAL_STATEMENT"), ("balance_sheet", "AUDITED_FINANCIAL_STATEMENT"), ("financial", "AUDITED_FINANCIAL_STATEMENT"),
    ("fdr", "CORPUS_FUND_FDR"), ("corpus", "CORPUS_FUND_FDR"), ("fixed_deposit", "CORPUS_FUND_FDR"),
    ("floor_plan", "FLOOR_PLAN"), ("area_statement", "FLOOR_PLAN"),
    ("society", "SOCIETY_TRUST_REGISTRATION"), ("trust", "SOCIETY_TRUST_REGISTRATION"),
    ("classroom", "INFRA_PHOTO_CLASSROOM"), ("computer_lab", "INFRA_PHOTO_COMPUTER_LAB"), ("computerlab", "INFRA_PHOTO_COMPUTER_LAB"),
    ("library", "INFRA_PHOTO_LIBRARY"), ("laboratory", "INFRA_PHOTO_LABORATORY"), ("_lab", "INFRA_PHOTO_LABORATORY"),
    ("ramp", "INFRA_PHOTO_ACCESSIBILITY"), ("accessib", "INFRA_PHOTO_ACCESSIBILITY"), ("divyang", "INFRA_PHOTO_ACCESSIBILITY"),
]
FILENAME_WEIGHT = 3.0

PHOTO_RULES: list[tuple[str, str, str]] = [
    (r"computer (lab|centre|center)|\bcomputers?\b|terminals?", "INFRA_PHOTO_COMPUTER_LAB", "computer lab signage"),
    (r"class ?room|lecture (hall|theatre)|tutorial", "INFRA_PHOTO_CLASSROOM", "classroom signage"),
    (r"library|reading (hall|room)", "INFRA_PHOTO_LIBRARY", "library signage"),
    (r"laborator|\blab\b|workshop", "INFRA_PHOTO_LABORATORY", "laboratory signage"),
    (r"ramp|\blift\b|divyang|accessib|barrier[- ]free|wheel ?chair", "INFRA_PHOTO_ACCESSIBILITY", "accessibility signage"),
]

_COMPILED = {dt: [(re.compile(rx, P), w, lab) for rx, w, lab in rules] for dt, rules in RULES.items()}


def _filename_hint(filename: str) -> tuple[str | None, str | None]:
    name = "_" + re.sub(r"[^a-z0-9]+", "_", Path(filename or "").stem.lower()) + "_"
    tokens = [t for t in name.split("_") if t]
    best = None
    for key, dt in FILENAME_HINTS:
        k = key.strip("_")
        if "_" in k:
            hit = f"_{k}_" in name or f"_{k}" in name
        elif len(k) >= 5:
            hit = any(t.startswith(k) for t in tokens)
        else:
            hit = k in tokens
        if hit and (best is None or len(k) > len(best[0])):
            best = (k, dt)
    return (best[1], best[0]) if best else (None, None)


def classify(text: str, filename: str = "") -> dict:
    text = text or ""
    ext = Path(filename or "").suffix.lower()
    scores: dict[str, float] = {dt: 0.0 for dt in RULES}
    reasons: dict[str, list[str]] = {dt: [] for dt in RULES}
    head = text[:6000]  # titles/letterheads carry most signal; body capped for robustness

    for dt, rules in _COMPILED.items():
        for rx, w, label in rules:
            m = rx.search(head) or (rx.search(text) if len(text) > 6000 else None)
            if m:
                # title-region bonus: the match occurs in the first ~400 chars
                bonus = 1.0 if m.start() < 400 and w >= 4 else 0.0
                scores[dt] += w + bonus
                reasons[dt].append(f"matched {label} '{m.group(0).strip()[:40]}' (+{w + bonus:g})")

    pans = PAN_RE.findall(text)
    if len(pans) >= 3:
        scores["FACULTY_ROSTER"] += 6
        reasons["FACULTY_ROSTER"].append(f"{len(pans)} PAN-format identifiers in tabular rows (+6)")

    # photos: little text -> rely on signage + filename
    is_image = ext in IMAGE_EXT
    text_len = len(re.sub(r"\s+", "", text))
    if is_image and text_len < 160:
        for dt in RULES:  # weak document evidence on a photo is mostly noise
            scores[dt] *= 0.3
        for rx, dt, label in PHOTO_RULES:
            m = re.search(rx, text, P)
            if m:
                scores[dt] = scores.get(dt, 0.0) + 5
                reasons.setdefault(dt, []).append(f"photo with {label} '{m.group(0)}' (+5)")
        if text_len < 160:
            for dt in ("INFRA_PHOTO_CLASSROOM", "INFRA_PHOTO_COMPUTER_LAB", "INFRA_PHOTO_LIBRARY",
                       "INFRA_PHOTO_LABORATORY", "INFRA_PHOTO_ACCESSIBILITY"):
                scores.setdefault(dt, 0.0)
                reasons.setdefault(dt, [])

    hint_dt, hint_key = _filename_hint(filename)
    if hint_dt:
        w = FILENAME_WEIGHT if not (is_image and hint_dt.startswith("INFRA_")) else FILENAME_WEIGHT + 2
        scores[hint_dt] = scores.get(hint_dt, 0.0) + w
        reasons.setdefault(hint_dt, []).append(f"filename hint '{hint_key}' (+{w:g})")

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top_dt, s1 = ranked[0]
    s2 = ranked[1][1] if len(ranked) > 1 else 0.0
    if s1 < 3:
        sig = ["no document-type evidence above threshold"]
        if is_image:
            sig.append("image with little readable text")
        return {"docType": "OTHER", "confidence": round(0.25 if s1 == 0 else 0.35, 2), "signals": sig,
                "scores": {k: round(v, 1) for k, v in ranked[:5]}}
    saturation = 1 - math.exp(-s1 / 7.0)
    margin = (s1 - s2) / s1
    conf = saturation * (0.45 + 0.55 * margin)
    signals = reasons.get(top_dt, [])[:6]
    if s2 > 0:
        signals.append(f"runner-up {ranked[1][0]} score {s2:g} vs {s1:g}")
    return {"docType": top_dt, "confidence": round(min(conf, 0.99), 2), "signals": signals,
            "scores": {k: round(v, 1) for k, v in ranked[:5]}}
