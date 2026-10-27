"""Rule-based field extraction per docType.

extract_fields(doc_type, text, ocr_confidence=1.0) -> {fieldName: {value, confidence, sourceText, page}}

* `text` is OcrResult.text (pages separated by "\f"; table cells on one visual row joined by 2 spaces).
* Dates are normalised to ISO (YYYY-MM-DD) from Indian formats (DD/MM/YYYY, DD-MM-YY, 12th March 2024, ...).
* Amounts understand Indian digit grouping (1,50,000) and Rs./INR/₹ prefixes; areas are numbers in the stated unit
  (hectares are converted to acres for landAreaAcres).
* Common fields: referenceNo, issuer, institutionName, issueDate, expiryDate (= valid upto / maturity / validTo).
"""
from __future__ import annotations

import csv
import io
import re
from datetime import date

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
_MON = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?"
DATE_RX = (
    rf"(?:\d{{1,2}}(?:st|nd|rd|th)?[\s\-./]*{_MON}[\s\-.,/]*\d{{4}}"
    rf"|{_MON}\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}"
    r"|\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}[./-]\d{1,2}[./-](?:\d{4}|\d{2}))"
)
REF_RX = r"[A-Z0-9][A-Z0-9/\-._]{2,60}[A-Z0-9]"
NUM_RX = r"\d[\d,]*(?:\.\d+)?"
AMOUNT_RX = r"(?:Rs\.?|INR|₹)?\s*\d[\d,]*(?:\.\d{1,2})?"
TEXT_RX = r"[^\n]{2,140}?(?=\s{2,}|\n|\f|$)"
PAN_RE = re.compile(r"\b[A-Z]{3}[PCHFATBLJG][A-Z]\d{4}[A-Z]\b")
AY_RE = re.compile(r"\b(20\d\d)\s?[-–/]\s?(\d{2}|20\d\d)\b")
SEP = r"\s*(?:[:\-–]|is|as|of|dated)?\s*"


# ----------------------------------------------------------------------------- normalisers
def parse_date(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip().rstrip(".,")
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        y, mo, d = map(int, m.groups())
        return _iso(y, mo, d)
    m = re.fullmatch(rf"(\d{{1,2}})(?:st|nd|rd|th)?[\s\-./]*({_MON})[\s\-.,/]*(\d{{4}})", s, re.I)
    if m:
        return _iso(int(m.group(3)), MONTHS.get(m.group(2)[:3].lower()), int(m.group(1)))
    m = re.fullmatch(rf"({_MON})\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})", s, re.I)
    if m:
        return _iso(int(m.group(3)), MONTHS.get(m.group(1)[:3].lower()), int(m.group(2)))
    m = re.fullmatch(r"(\d{1,2})[./-](\d{1,2})[./-](\d{4}|\d{2})", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000 if y < 70 else 1900
        if mo > 12 and d <= 12:  # tolerate MM/DD when unambiguous
            d, mo = mo, d
        return _iso(y, mo, d)
    return None


def _iso(y, mo, d) -> str | None:
    try:
        return date(int(y), int(mo), int(d)).isoformat() if mo else None
    except (TypeError, ValueError):
        return None


def parse_number(s: str | None) -> float | None:
    if s is None:
        return None
    s = re.sub(r"(?i)rs\.?|inr|₹|/-", "", str(s)).replace(",", "").strip()
    m = re.search(r"\d+(?:\.\d+)?", s)
    return float(m.group(0)) if m else None


def _num(v: float | None):
    if v is None:
        return None
    return int(v) if float(v).is_integer() else round(v, 4)


def academic_year(s: str) -> str | None:
    m = AY_RE.search(s or "")
    if not m:
        return None
    a, b = m.group(1), m.group(2)
    return f"{a}-{b[-2:]}"


# ----------------------------------------------------------------------------- helpers
def _line_at(text: str, start: int, end: int) -> str:
    ls = max(text.rfind("\n", 0, start), text.rfind("\f", 0, start)) + 1
    le_candidates = [i for i in (text.find("\n", end), text.find("\f", end)) if i != -1]
    le = min(le_candidates) if le_candidates else len(text)
    return re.sub(r"\s{2,}", "  ", text[ls:le].strip())[:200]


def _page_of(text: str, pos: int) -> int:
    return text.count("\f", 0, pos) + 1


def _field(text, value, conf, start, end):
    return {"value": value, "confidence": round(conf, 2), "sourceText": _line_at(text, start, end), "page": _page_of(text, start)}


def _find(text: str, labels: list[str], value_rx: str, flags=re.I):
    """First match of any label (in priority order) followed by a value. Returns (value, start, end) or None."""
    for lab in labels:
        rx = re.compile(rf"(?:{lab}){SEP}(?P<v>{value_rx})", flags)
        m = rx.search(text)
        if m:
            return m.group("v").strip(), m.start(), m.end()
    return None


class _Out(dict):
    def __init__(self, text: str, ocr_conf: float):
        super().__init__()
        self.text = text
        self.k = 0.6 + 0.4 * max(0.0, min(1.0, ocr_conf))

    def put(self, name, value, conf, start, end, overwrite=False):
        if value in (None, "", []):
            return
        if name in self and not overwrite:
            return
        self[name] = _field(self.text, value, conf * self.k, start, end)

    def date(self, name, labels, conf=0.9):
        r = _find(self.text, labels, DATE_RX)
        if r:
            self.put(name, parse_date(r[0]), conf, r[1], r[2])

    def ref(self, name, labels, conf=0.9, rx=REF_RX):
        # OCR frequently joins label words (e.g. MutationEntryNo.). Keep
        # reference values exact; tolerate missing spaces only in labels.
        r = _find(self.text, [label.replace(r"\s+", r"\s*") for label in labels], rx)
        if r:
            self.put(name, r[0].rstrip(".,;"), conf, r[1], r[2])

    def textf(self, name, labels, conf=0.85):
        r = _find(self.text, labels, TEXT_RX)
        if r:
            self.put(name, r[0].strip(" ,.;:"), conf, r[1], r[2])

    def number(self, name, labels, conf=0.88, unit_rx: str | None = None, factor: float = 1.0):
        rx = NUM_RX + (rf"\s*(?:{unit_rx})" if unit_rx else "")
        r = _find(self.text, labels, rx)
        if r:
            self.put(name, _num(parse_number(r[0]) * factor), conf, r[1], r[2])

    def amount(self, name, labels, conf=0.88):
        r = _find(self.text, labels, AMOUNT_RX)
        if r:
            self.put(name, _num(parse_number(r[0])), conf, r[1], r[2])


# ----------------------------------------------------------------------------- per-type label sets
REF_LABELS = {
    "FIRE_NOC": [r"(?:Fire\s+)?NOC\s+No\.?", r"Certificate\s+No\.?", r"Ref(?:erence)?\.?\s*No\.?"],
    "LAND_DOCUMENT": [r"(?:Registration|Regn\.?|Document|Deed)\s+No\.?", r"Mutation\s+(?:Entry\s+)?No\.?", r"Ref(?:erence)?\.?\s*No\.?"],
    "BUILDING_PLAN_APPROVAL": [r"(?:Building\s+)?Permit\s+No\.?", r"Permission\s+No\.?", r"Plan\s+Approval\s+No\.?",
                               r"Commencement\s+Certificate\s+No\.?", r"Ref(?:erence)?\.?\s*No\.?"],
    "OCCUPANCY_CERTIFICATE": [r"(?:OC|Occupancy\s+Certificate|Completion\s+Certificate)\s+No\.?", r"Certificate\s+No\.?", r"Ref(?:erence)?\.?\s*No\.?"],
    "STRUCTURAL_STABILITY_CERT": [r"Certificate\s+No\.?", r"Ref(?:erence)?\.?\s*No\.?"],
    "AFFIDAVIT_UNDERTAKING": [r"e-?Stamp\s+(?:Certificate\s+)?No\.?", r"Stamp\s+(?:Paper\s+)?No\.?", r"Certificate\s+No\.?", r"Notarial\s+Reg(?:istration|n)?\.?\s+No\.?"],
    "UNIVERSITY_AFFILIATION": [r"Letter\s+No\.?", r"Ref(?:erence)?\.?\s*No\.?", r"\bNo\."],
    "STATE_GOVT_NOC": [r"NOC\s*No\.?", r"Letter\s+No\.?", r"G\.?\s?R\.?\s+No\.?", r"Ref(?:erence)?\.?\s*No\.?", r"\bNo\."],
    "PREVIOUS_EOA_LETTER": [r"F\.\s?No\.?", r"File\s+No\.?", r"Letter\s+No\.?", r"Ref(?:erence)?\.?\s*No\.?"],
    "NBA_ACCREDITATION": [r"Accreditation\s+(?:Ref(?:erence)?|No\.?|Certificate\s+No\.?)\.?\s*(?:No\.?)?", r"Certificate\s+No\.?", r"Ref(?:erence)?\.?\s*No\.?"],
    "NAAC_ACCREDITATION": [r"(?:EC|Certificate|Accreditation)\s+No\.?", r"Ref(?:erence)?\.?\s*No\.?"],
    "TER_PAYMENT_RECEIPT": [r"Transaction\s+(?:ID|No\.?|Reference)", r"Txn\.?\s+(?:ID|No\.?)", r"\bUTR(?:\s+No\.?)?"],
    "AUDITED_FINANCIAL_STATEMENT": [r"\bUDIN"],
    "CORPUS_FUND_FDR": [r"FDR\s+No\.?", r"(?:Fixed|Term)\s+Deposit\s+(?:Receipt\s+)?No\.?", r"Deposit\s+No\.?", r"Receipt\s+No\.?"],
    "FLOOR_PLAN": [r"Drawing\s+No\.?", r"Ref(?:erence)?\.?\s*No\.?"],
    "SOCIETY_TRUST_REGISTRATION": [r"Registration\s+No\.?", r"Reg(?:n)?\.\s+No\.?", r"Ref(?:erence)?\.?\s*No\.?"],
}
GENERIC_REF = [r"Ref(?:erence)?\.?\s*No\.?", r"Certificate\s+No\.?"]
ISSUE_LABELS = [r"Date\s+of\s+(?:Issue|Registration|Payment|Deposit|Approval|Accreditation\s+Decision)", r"Issue\s+Date",
                r"Issued\s+on", r"Payment\s+Date", r"Deposit\s+Date", r"\bDate(?=\s*:)", r"Dated", r"Date"]
EXPIRY_LABELS = [r"Valid\s+(?:up\s?to|till|until|upto|through)", r"Validity(?:\s+(?:up\s?to|till|period\s+up\s?to))?",
                 r"(?:Date\s+of\s+)?Expiry(?:\s+Date)?", r"Expires\s+on", r"Valid\s+To", r"Accredited\s+up\s?to"]
INSTITUTION_LABELS = [r"Name\s+of\s+(?:the\s+)?(?:Institut(?:e|ion)|College)", r"Institut(?:e|ion)\s+Name",
                      r"(?:Institut(?:e|ion)|College|Applicant\s+Institution)(?=\s*:)"]
INST_FALLBACK = re.compile(
    r"\b((?:[A-Z][A-Za-z&.'-]+\s){1,5}(?:Institute|College)\s+(?:of|for)\s+(?:(?:[A-Z][A-Za-z&.'-]*|&|and)\s?){1,6})")
SPECIMEN_RE = re.compile(r"specimen|synthetic|simulated|not a real", re.I)


def _issuer(out: _Out, text: str):
    first_page = text.split("\f", 1)[0]
    pos = 0
    for line in first_page.split("\n"):
        s = line.strip()
        if len(s) >= 8 and not SPECIMEN_RE.search(s) and re.search(r"[A-Za-z]{4}", s):
            cand = re.split(r"\s{2,}", s)[0]
            if len(cand) >= 8:
                start = text.find(cand, pos)
                out.put("issuer", cand.strip(" ,"), 0.6, max(start, 0), max(start, 0) + len(cand))
                return
        pos += len(line) + 1


def _institution(out: _Out, text: str):
    r = _find(text, [r"^\s*" + label + r"(?=\s*:|\s{2,})" for label in INSTITUTION_LABELS], TEXT_RX, flags=re.I | re.M)
    if r and re.search(r"[A-Za-z]{3}", r[0]):
        out.put("institutionName", r[0].strip(" ,.;:"), 0.88, r[1], r[2])
        return
    m = INST_FALLBACK.search(text)
    if m:
        name = re.sub(r"\s+(and|&)$", "", m.group(1).strip(" ,.&"))
        out.put("institutionName", name, 0.62, m.start(1), m.end(1))


def _validity_range(out: _Out, text: str, conf=0.9):
    m = re.search(rf"(?:valid(?:ity)?|accredit\w*|period)[^\n]{{0,60}}?from\s+(?P<a>{DATE_RX})\s+(?:to|till|until|up\s?to)\s+(?P<b>{DATE_RX})", text, re.I)
    if m:
        out.put("validFrom", parse_date(m.group("a")), conf, m.start("a"), m.end("a"), overwrite=True)
        out.put("expiryDate", parse_date(m.group("b")), conf, m.start("b"), m.end("b"), overwrite=True)


def _academic_year(out: _Out, text: str, conf=0.85):
    m = re.search(r"(?:academic\s+(?:year|session)|A\.Y\.?|session)\s*[:\-]?\s*(20\d\d\s?[-–/]\s?(?:\d{2}|20\d\d))", text, re.I)
    if not m:
        m = AY_RE.search(text)
        conf = 0.6
        if m:
            out.put("academicYear", academic_year(m.group(0)), conf, m.start(), m.end())
        return
    out.put("academicYear", academic_year(m.group(1)), conf, m.start(1), m.end(1))


# ----------------------------------------------------------------------------- faculty roster
DESIG_RX = re.compile(r"\b(Professor|Associate\s+Professor|Assistant\s+Professor|Asst\.?\s*Prof\.?|Assoc\.?\s*Prof\.?|Prof\.?)\b", re.I)
QUAL_RX = re.compile(r"\b(Ph\.?\s?D|M\.?\s?Tech|M\.?\s?E\.?|M\.?\s?Sc|M\.?\s?B\.?A|M\.?\s?C\.?A|B\.?\s?Tech|M\.?\s?Phil|MBA|MCA)\b", re.I)
DEPT_RX = re.compile(r"(Engineering|Science|Mathematics|Physics|Chemistry|Humanities|Management|Computer|Electronics|Electrical|Mechanical|Civil|Information|Applied|Artificial)", re.I)
_HEADER_MAP = {
    "name": "name", "facultyname": "name", "nameofthefaculty": "name", "nameoffaculty": "name",
    "pan": "pan", "panno": "pan", "pannumber": "pan", "pancard": "pan",
    "designation": "designation", "department": "department", "dept": "department",
    "qualification": "qualification", "highestqualification": "qualification",
    "dateofjoining": "joiningDate", "doj": "joiningDate", "joiningdate": "joiningDate",
    "facultyid": "facultyId", "aicteid": "facultyId", "uniqueid": "facultyId", "id": "facultyId", "empid": "facultyId",
    "employeeid": "facultyId",
}


def _cadre(designation: str) -> str:
    d = designation.lower()
    if "assist" in d or "asst" in d:
        return "assistantProfessor"
    if "assoc" in d:
        return "associateProfessor"
    if "prof" in d:
        return "professor"
    return "other"


def _roster_rows_csv(text: str) -> list[dict] | None:
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines or "," not in lines[0] and "\t" not in lines[0]:
        return None
    delim = "\t" if lines[0].count("\t") > lines[0].count(",") else ","
    reader = csv.reader(io.StringIO("\n".join(lines)), delimiter=delim)
    rows = list(reader)
    header_idx = None
    for i, r in enumerate(rows[:10]):
        keys = [re.sub(r"[^a-z]", "", c.lower()) for c in r]
        if any(k in ("pan", "panno", "pannumber", "pancard") for k in keys):
            header_idx = i
            break
    if header_idx is None:
        return None
    cols = [_HEADER_MAP.get(re.sub(r"[^a-z]", "", c.lower())) for c in rows[header_idx]]
    out = []
    for lineno, r in enumerate(rows[header_idx + 1:], start=header_idx + 2):
        rec = {c: v.strip() for c, v in zip(cols, r) if c}
        if not rec.get("pan") and not rec.get("name"):
            continue
        rec["pan"] = rec.get("pan", "").upper()
        if rec.get("joiningDate"):
            rec["joiningDate"] = parse_date(rec["joiningDate"]) or rec["joiningDate"]
        rec["_line"] = lineno
        out.append(rec)
    return out


def _roster_rows_table(text: str) -> list[dict]:
    out = []
    for line in text.replace("\f", "\n").splitlines():
        m = PAN_RE.search(line)
        if not m:
            continue
        cells = [c.strip() for c in re.split(r"\s{2,}|\|", line) if c.strip()]
        rec = {"pan": m.group(0)}
        for c in cells:
            if PAN_RE.fullmatch(c):
                continue
            if "designation" not in rec and DESIG_RX.fullmatch(c.strip()):
                rec["designation"] = c
            elif "qualification" not in rec and QUAL_RX.match(c):
                rec["qualification"] = c
            elif "joiningDate" not in rec and parse_date(c):
                rec["joiningDate"] = parse_date(c)
            elif "facultyId" not in rec and re.fullmatch(r"(?:[A-Z]{1,5}[-/]?)?\d[\d\-/]{3,}", c):
                rec["facultyId"] = c
            elif re.fullmatch(r"\d{1,4}\.?", c):
                continue  # serial number
            elif "department" not in rec and DEPT_RX.search(c) and not re.match(r"(Dr|Prof|Mr|Ms|Mrs)\.?\s", c):
                rec["department"] = c
            elif "name" not in rec and re.fullmatch(r"[A-Za-z][A-Za-z.' ]{2,60}", c):
                rec["name"] = c
        out.append(rec)
    return out


def _extract_roster(out: _Out, text: str):
    rows = _roster_rows_csv(text)
    tabular = rows is not None
    if rows is None:
        rows = _roster_rows_table(text)
    for r in rows:
        r.setdefault("designation", "")
    cadre = {"professor": 0, "associateProfessor": 0, "assistantProfessor": 0, "other": 0}
    for r in rows:
        cadre[_cadre(r.get("designation", ""))] += 1
    depts: dict[str, int] = {}
    for r in rows:
        if r.get("department"):
            depts[r["department"]] = depts.get(r["department"], 0) + 1
    first = PAN_RE.search(text)
    start = first.start() if first else 0
    conf = 0.95 if tabular else 0.85
    clean_rows = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    out.put("facultyCount", len(rows), conf, start, start + 10)
    out.put("pans", [r["pan"] for r in rows if r.get("pan")], conf, start, start + 10)
    out.put("faculty", clean_rows, conf, start, start + 10)
    out.put("cadre", cadre, conf * 0.95, start, start + 10)
    if depts:
        out.put("departments", depts, conf * 0.9, start, start + 10)
    m = re.search(r"total\s+(?:number\s+of\s+)?(?:teaching\s+)?faculty(?:\s+members)?\s*[:\-=]?\s*(\d{1,4})", text, re.I)
    if m:
        out.put("declaredTotal", int(m.group(1)), 0.9, m.start(1), m.end(1))
    invalid = [r.get("pan") for r in rows if r.get("pan") and not PAN_RE.fullmatch(r["pan"])]
    if invalid:
        out.put("invalidPans", invalid, 0.9, start, start + 10)


# ----------------------------------------------------------------------------- main entry
def extract_fields(doc_type: str, text: str, ocr_confidence: float = 1.0) -> dict:
    text = text or ""
    out = _Out(text, ocr_confidence)
    if doc_type.startswith("INFRA_PHOTO") or not text.strip():
        return dict(out)

    if doc_type == "FACULTY_ROSTER":
        _institution(out, text)
        _extract_roster(out, text)
        _academic_year(out, text)
        return dict(out)

    out.ref("referenceNo", REF_LABELS.get(doc_type, []) + GENERIC_REF)
    _issuer(out, text)
    _institution(out, text)

    t = doc_type
    if t == "LAND_DOCUMENT":
        out.ref("surveyNo", [r"Survey\s+No\.?", r"Gat\s+No\.?", r"Khasra\s+No\.?", r"S\.\s?No\.", r"Plot\s+No\.?"],
                rx=r"[0-9][0-9A-Za-z/\-]*")
        out.number("landAreaAcres", [r"(?:Total\s+)?(?:Land\s+)?Area(?:\s+of\s+(?:the\s+)?land)?", r"admeasuring", r"measuring"],
                   unit_rx=r"acres?|ac\b")
        if "landAreaAcres" not in out:
            out.number("landAreaAcres", [r"(?:Total\s+)?(?:Land\s+)?Area", r"admeasuring", r"measuring"],
                       unit_rx=r"hectares?|ha\b", factor=2.47105, conf=0.8)
        out.textf("ownerName", [r"(?:Name\s+of\s+(?:the\s+)?)?(?:Purchaser|Vendee|Lessee|Owner|Occupant|Khatedar)(?:\s+Name)?(?=\s*:)"])
        out.textf("village", [r"Village(?=\s*:)", r"Mouje(?=\s*:)"])
        out.textf("district", [r"District(?=\s*:)"])
        out.date("issueDate", [r"Date\s+of\s+Registration", r"Registered\s+on"] + ISSUE_LABELS)
    elif t in ("BUILDING_PLAN_APPROVAL", "OCCUPANCY_CERTIFICATE", "FLOOR_PLAN"):
        out.number("builtUpAreaSqm", [r"(?:Total\s+)?(?:Sanctioned\s+)?Built[- ]?up\s+Area(?:\s+\(?sq\.?\s?m\.?\)?)?",
                                      r"Total\s+(?:Floor|Covered)\s+Area"], unit_rx=r"sq\.?\s?m(?:tr|etres?|eters?)?\.?|m2|m²|square\s+met(?:re|er)s?")
        out.number("floors", [r"No\.?\s+of\s+Floors", r"Number\s+of\s+floors"], conf=0.8)
        if t == "FLOOR_PLAN":
            out.number("classrooms", [r"(?:No\.?\s+of\s+)?Class\s?rooms?\s*\(?(?:nos\.?)?\)?(?=\s*:)"], conf=0.75)
            out.number("laboratories", [r"(?:No\.?\s+of\s+)?Laborator(?:y|ies)\s*\(?(?:nos\.?)?\)?(?=\s*:)"], conf=0.75)
            out.textf("architect", [r"Architect(?=\s*:)", r"Prepared\s+by"])
    elif t == "FIRE_NOC":
        out.textf("occupancyType", [r"Occupancy\s+(?:Type|Classification)", r"Type\s+of\s+(?:Building|Occupancy)"], conf=0.8)
        out.number("buildingHeightM", [r"(?:Building\s+)?Height"], unit_rx=r"m(?:tr|etres?|eters?)?\b", conf=0.8)
    elif t == "STRUCTURAL_STABILITY_CERT":
        out.textf("engineerName", [r"(?:Name\s+of\s+)?(?:Structural\s+)?Engineer(?=\s*:)", r"Certified\s+by"])
        out.ref("licenceNo", [r"Licen[cs]e\s+No\.?", r"Registration\s+No\.?"])
    elif t == "AFFIDAVIT_UNDERTAKING":
        out.textf("deponentName", [r"\bDeponent(?=\s*:)"])
        m = re.search(r"\bI,\s+([A-Z][A-Za-z.' ]{3,60}?),", text)
        if m:
            out.put("deponentName", m.group(1).strip(), 0.8, m.start(1), m.end(1))
        out.date("notarisedOn", [r"Notari[sz]ed\s+on", r"Attested\s+(?:on|before\s+me\s+on)", r"Sworn\s+(?:before\s+me\s+)?on"])
        out.date("issueDate", [r"(?:e-?Stamp\s+)?(?:Issue|Certificate\s+Issued)\s+Date", r"Date\s+of\s+Issue"] + ISSUE_LABELS)
        _academic_year(out, text)
    elif t in ("UNIVERSITY_AFFILIATION", "STATE_GOVT_NOC"):
        _academic_year(out, text)
        out.number("totalIntake", [r"Total\s+(?:Approved\s+|Sanctioned\s+|Permitted\s+)?Intake", r"intake\s+(?:capacity\s+)?of"], conf=0.82)
        m = re.search(r"^[^\n]*\bUniversity\b[^\n]*$", text, re.M)
        if m and t == "UNIVERSITY_AFFILIATION":
            uni = re.split(r"\s{2,}", m.group(0).strip())[0]
            out.put("university", uni, 0.7, m.start(), m.end())
        out.textf("proposedName", [r"(?:Proposed|New)\s+Name(?:\s+of\s+(?:the\s+)?Institut(?:e|ion))?"], conf=0.85)
        out.textf("course", [r"(?:Name\s+of\s+(?:the\s+)?)?(?:New\s+)?(?:Course|Programme)(?=\s*:)"], conf=0.8)
        out.textf("affiliationType", [r"(?:Nature|Type)\s+of\s+Affiliation"], conf=0.8)
    elif t == "PREVIOUS_EOA_LETTER":
        m = re.search(r"\b1-\d{7,10}\b", text)
        if m:
            out.put("permanentId", m.group(0), 0.9, m.start(), m.end())
        _academic_year(out, text)
        out.number("totalIntake", [r"Total\s+(?:Approved\s+)?Intake"], conf=0.85)
        out.textf("approvalStatus", [r"Approval\s+Status", r"Status"], conf=0.7)
    elif t == "NBA_ACCREDITATION":
        out.textf("programme", [r"Name\s+of\s+(?:the\s+)?Programme", r"Programme(?:\s+Name)?(?=\s*:)", r"Program(?=\s*:)"])
        out.textf("tier", [r"Tier(?=\s*:)", r"Accreditation\s+Category"], conf=0.8)
        _validity_range(out, text)
        out.date("validFrom", [r"Valid\s+From", r"Accredited\s+from"])
    elif t == "NAAC_ACCREDITATION":
        m = re.search(r"\bGrade\s*[:\-]?\s*['\"“]?(A\+\+|A\+|A|B\+\+|B\+|B|C|D)(?![A-Za-z])", text)
        if m:
            out.put("grade", m.group(1), 0.9, m.start(1), m.end(1))
        m = re.search(r"\bCGPA\s*(?:of)?\s*[:\-]?\s*(\d\.\d{1,2})", text)
        if m:
            out.put("cgpa", float(m.group(1)), 0.9, m.start(1), m.end(1))
        out.textf("cycle", [r"Cycle(?=\s*:)"], conf=0.75)
        _validity_range(out, text)
    elif t == "TER_PAYMENT_RECEIPT":
        out.amount("amount", [r"Amount\s+(?:Paid|Received)(?:\s*\(.{0,6}\))?", r"Total\s+Amount", r"Amount(?:\s*\(.{0,6}\))?"])
        out.date("issueDate", [r"(?:Payment|Transaction)\s+Date(?:\s*(?:&|and)\s*Time)?", r"Paid\s+on"] + ISSUE_LABELS)
        out.textf("paymentStatus", [r"(?:Payment|Transaction)\s+Status", r"Status"], conf=0.85)
        out.ref("applicationNo", [r"Application\s+(?:No\.?|Number|ID)"], conf=0.85)
        _academic_year(out, text)
    elif t == "AUDITED_FINANCIAL_STATEMENT":
        out.ref("udin", [r"\bUDIN"], rx=r"\d{8}[A-Z0-9]{10}")
        m = re.search(r"(?:F\.?\s?Y\.?|financial\s+year|year\s+ended?)\s*[:\-]?\s*(?:31(?:st)?\s+March,?\s+)?(20\d\d\s?[-–]\s?\d{2,4}|20\d\d)", text, re.I)
        if m:
            fy = m.group(1)
            out.put("financialYear", academic_year(fy) if "-" in fy or "–" in fy else f"{int(fy) - 1}-{fy[-2:]}", 0.8, m.start(1), m.end(1))
        out.ref("membershipNo", [r"M(?:embership)?\.?\s*No\.?"], rx=r"\d{5,7}")
        out.ref("firmRegNo", [r"F(?:irm)?\.?\s*R(?:eg(?:istration)?)?\.?\s*N(?:o|umber)\.?", r"\bFRN"], rx=r"[0-9]{5,7}[A-Z]?")
        out.textf("auditorFirm", [r"For\s+(?=M/s)"], conf=0.7)
        out.amount("totalIncome", [r"Total\s+Income", r"Total\s+Receipts"], conf=0.75)
    elif t == "CORPUS_FUND_FDR":
        out.amount("amount", [r"(?:Deposit|Principal)\s+Amount", r"Amount\s+of\s+Deposit", r"Amount"])
        out.date("issueDate", [r"Date\s+of\s+Deposit", r"Deposit\s+Date"] + ISSUE_LABELS)
        out.date("expiryDate", [r"Maturity\s+Date", r"Date\s+of\s+Maturity", r"Due\s+Date"])
        out.number("interestRate", [r"Rate\s+of\s+Interest", r"Interest\s+Rate"], unit_rx=r"%", conf=0.8)
        m = re.search(r"^[^\n]*\bBank\b[^\n]*$", text, re.M)
        if m:
            out.put("bankName", re.split(r"\s{2,}", m.group(0).strip())[0], 0.65, m.start(), m.end())
    elif t == "SOCIETY_TRUST_REGISTRATION":
        out.textf("trustName", [r"Name\s+of\s+(?:the\s+)?(?:Society|Trust)", r"(?:Society|Trust)\s+Name"])
        out.date("issueDate", [r"Date\s+of\s+Registration", r"Registered\s+on"] + ISSUE_LABELS)
        out.textf("newInstitutionName", [r"(?:changed|amended)\s+to", r"New\s+Name\s+of\s+(?:the\s+)?Institut(?:e|ion)", r"Proposed\s+Name"], conf=0.8)

    out.date("issueDate", ISSUE_LABELS, conf=0.8)
    out.date("expiryDate", EXPIRY_LABELS, conf=0.88)
    return dict(out)
