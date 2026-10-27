"""Generate the synthetic VeriSense dataset (fictional institutions, authorities and people).

    cd backend && uv run python ../samples/tools/generate.py

Outputs
  samples/<inst>/...               PDFs, scans (JPG / image-only PDF), CSV roster, geo-tagged infra photos
  samples/benchmark/...            forensic benchmark (clean vs tampered scans / PDFs) for precision-recall
  samples/scenarios.json           institutions + InstitutionalRecords, 6 applications, authorityRecords, ground truth
  samples/tools/keys/<kid>.pem     Ed25519 PRIVATE keys of simulated issuers (generator only)
  backend/config/authority_keys/   matching PUBLIC keys (+ issuers.json)

Deterministic: fixed seeds; keys are created once and reused.
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
import shutil
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAMPLES = HERE.parent
REPO = SAMPLES.parent
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(HERE))

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from PIL import ImageFilter  # noqa: E402

import render as R  # noqa: E402
from app.pipeline.signature import sign_claims  # noqa: E402

PRIV_DIR = HERE / "keys"
PUB_DIR = REPO / "backend" / "config" / "authority_keys"
REFERENCE_DATE = "2026-10-26"
AY = "2027-28"

# ============================================================================= issuers & keys
ISSUERS = {
    "aicte-approvals": ("All India Council for Technical Education (simulated)", "aicte_eoa"),
    "fire-pmr": ("Pune Metropolitan Region Fire & Emergency Services (simulated)", "municipal_fire"),
    "fire-vuf": ("Vadodara Urban Fire Safety Directorate (simulated)", "municipal_fire"),
    "fire-gn": ("Greater Noida Fire & Rescue Services (simulated)", "municipal_fire"),
    "bpc-pmr": ("Pune Metropolitan Region Development Authority (simulated)", "municipal_fire"),
    "bpc-vmda": ("Vadodara Metropolitan Development Authority (simulated)", "municipal_fire"),
    "bpc-gn": ("Greater Noida Urban Planning Board (simulated)", "municipal_fire"),
    "nbep": ("National Accreditation Board for Engineering Programmes (simulated)", "nba"),
    "niac": ("National Institutional Assessment Council (simulated)", "naac"),
    "univ-stu": ("Sahyadri Technological University (simulated)", "digilocker"),
    "univ-ntu": ("Narmada Technological University (simulated)", "digilocker"),
    "univ-gangtu": ("Gangetic Technical University (simulated)", "digilocker"),
    "dte-mh": ("Directorate of Technical Education, Maharashtra (simulated)", "digilocker"),
}
KEYS: dict[str, Ed25519PrivateKey] = {}


def ensure_keys():
    PRIV_DIR.mkdir(parents=True, exist_ok=True)
    PUB_DIR.mkdir(parents=True, exist_ok=True)
    registry = {}
    for kid, (issuer, source) in ISSUERS.items():
        kid_full = f"{kid}-2026"
        priv_path = PRIV_DIR / f"{kid_full}.pem"
        if priv_path.exists():
            key = serialization.load_pem_private_key(priv_path.read_bytes(), password=None)
        else:
            key = Ed25519PrivateKey.generate()
            priv_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                    serialization.NoEncryption()))
        (PUB_DIR / f"{kid_full}.pub").write_bytes(key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
        KEYS[kid] = key
        registry[kid_full] = {"issuer": issuer, "sourceId": source, "simulated": True}
    (PUB_DIR / "issuers.json").write_text(json.dumps(registry, indent=2), encoding="utf-8")
    (PRIV_DIR / "README.txt").write_text(
        "Ed25519 PRIVATE keys of the SIMULATED issuers used only by samples/tools/generate.py to sign QR codes.\n"
        "They protect nothing real. Public halves: backend/config/authority_keys/.\n", encoding="utf-8")


def qr(kid: str, claims: dict) -> str:
    return sign_claims(KEYS[kid], ISSUERS[kid][0], f"{kid}-2026", claims)


def forged_qr(kid: str, claims_signed: dict, claims_shown: dict) -> str:
    """Payload whose claims were edited after signing (signature no longer verifies)."""
    from app.pipeline.signature import b64u_decode, b64u_encode, canonical_json

    env = json.loads(b64u_decode(qr(kid, claims_signed)))
    env["claims"] = claims_shown
    return b64u_encode(canonical_json(env))


# ============================================================================= people
FIRST = ["Aarti", "Abhijit", "Aditi", "Ajay", "Amit", "Anagha", "Anil", "Anjali", "Ankit", "Arvind", "Ashwini", "Bhavesh",
         "Chetan", "Deepa", "Dhruv", "Gauri", "Girish", "Harsha", "Hemant", "Isha", "Jayesh", "Kalpana", "Kiran", "Kunal",
         "Lata", "Mahesh", "Manisha", "Meera", "Milind", "Mohan", "Neha", "Nikhil", "Nisha", "Omkar", "Pallavi", "Pankaj",
         "Pooja", "Prakash", "Pranav", "Priya", "Rahul", "Rajesh", "Rashmi", "Rohit", "Ruchi", "Sachin", "Sandeep", "Sanjay",
         "Shalini", "Shilpa", "Shreya", "Sneha", "Sunil", "Swati", "Tejas", "Uday", "Vaishali", "Varun", "Vijay", "Vinita",
         "Yogesh", "Zoya", "Farhan", "Imran", "Sana", "Ravindra", "Gurpreet", "Harpreet", "Arjun", "Kavya"]
LAST = ["Apte", "Bhatt", "Chavan", "Deshmukh", "Desai", "Gaikwad", "Gupta", "Iyer", "Jadhav", "Joshi", "Kale", "Kulkarni",
        "Mehta", "Mishra", "Nair", "Pandey", "Patel", "Patil", "Pawar", "Rao", "Saxena", "Shah", "Sharma", "Shinde",
        "Singh", "Srivastava", "Tiwari", "Trivedi", "Verma", "Yadav", "Qureshi", "Khan", "Bose", "Menon", "Rathod", "Chauhan"]
QUALS = {"professor": ["Ph.D", "Ph.D"], "associateProfessor": ["Ph.D", "Ph.D", "M.Tech"], "assistantProfessor": ["M.Tech", "M.E", "M.Tech", "Ph.D"]}
DESIG = {"professor": "Professor", "associateProfessor": "Associate Professor", "assistantProfessor": "Assistant Professor"}


def make_pan(rng, last):
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    return "".join(rng.choice(letters) for _ in range(3)) + "P" + last[0].upper() + f"{rng.randint(1000, 9999)}" + rng.choice(letters)


def make_faculty(seed, n, prefix, depts):
    rng = random.Random(seed)
    prof = max(1, round(n / 9))
    assoc = max(1, round(2 * n / 9))
    cad = ["professor"] * prof + ["associateProfessor"] * assoc + ["assistantProfessor"] * (n - prof - assoc)
    used, rows = set(), []
    for i, c in enumerate(cad):
        while True:
            fn, ln = rng.choice(FIRST), rng.choice(LAST)
            if (fn, ln) not in used:
                used.add((fn, ln))
                break
        title = "Dr. " if c != "assistantProfessor" or rng.random() < 0.2 else ("Mr. " if rng.random() < 0.5 else "Ms. ")
        q = rng.choice(QUALS[c])
        if title == "Dr. ":
            q = "Ph.D"
        rows.append({"facultyId": f"{prefix}-{1001 + i}", "name": f"{title}{fn} {ln}", "pan": make_pan(rng, ln),
                     "designation": DESIG[c], "qualification": q, "department": depts[i % len(depts)],
                     "joiningDate": f"{rng.randint(2008, 2025)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"})
    return rows


def mask_pan(p):
    return p[:4] + "X" * 4 + p[8:]


def record_faculty(rows):
    return [{"facultyId": r["facultyId"], "name": r["name"], "panMasked": mask_pan(r["pan"]),
             "panHash": hashlib.sha256(r["pan"].encode()).hexdigest()[:16],
             "designation": r["designation"], "qualification": r["qualification"], "department": r["department"],
             "joiningDate": r["joiningDate"]} for r in rows]


def dmy(iso, style="slash"):
    y, m, d = iso.split("-")
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    if style == "slash":
        return f"{d}/{m}/{y}"
    if style == "dash":
        return f"{d}-{m}-{y}"
    if style == "dot":
        return f"{d}.{m}.{y}"
    if style == "long":
        n = int(d)
        suf = "th" if 11 <= n <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suf} {months[int(m) - 1]} {y}"
    if style == "us":
        return f"{months[int(m) - 1]} {int(d)}, {y}"
    raise ValueError(style)


def dt(iso, h=11, mi=0):
    y, m, d = map(int, iso.split("-"))
    return datetime(y, m, d, h, mi, 0)


def inr(n):
    s = str(int(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return f"Rs. {s}.00"


# ============================================================================= institutions
INST = {
    "piat": dict(key="piat", permanentId="1-3948291012", name="Pragati Institute of Advanced Technology",
                 type="Private-Self Financing", state="Maharashtra", city="Pune", region="WR", establishedYear=2009,
                 trustName="Pragati Shikshan Prasarak Mandal",
                 address="Survey No. 112/3, Maan-Hinjawadi Road, Mulshi, Pune - 411057",
                 campusGps={"lat": 18.5913, "lng": 73.7389}),
    "apex": dict(key="apex", permanentId="1-8492048217", name="Apex Valley Institute of Technology & Management",
                 type="Private-Self Financing", state="Uttar Pradesh", city="Greater Noida", region="NR", establishedYear=2011,
                 trustName="Apex Valley Educational Trust",
                 address="Plot No. 27, Knowledge Park V, Greater Noida, Gautam Buddh Nagar - 201310",
                 campusGps={"lat": 28.4744, "lng": 77.5040}),
    "nvie": dict(key="nvie", permanentId="1-1029482233", name="Narmada Valley Institute of Engineering",
                 type="Private-Self Financing", state="Gujarat", city="Vadodara", region="WR", establishedYear=2006,
                 trustName="Narmada Vidya Pratishthan",
                 address="Block No. 45, Waghodia Road, Vadodara - 391760",
                 campusGps={"lat": 22.2990, "lng": 73.3570}),
}

PROGRAMMES = {
    "piat": [("UG", "B.Tech", "Computer Engineering", 120), ("UG", "B.Tech", "Information Technology", 60),
             ("UG", "B.Tech", "Electronics & Telecommunication Engineering", 60), ("UG", "B.Tech", "Mechanical Engineering", 60)],
    "apex": [("UG", "B.Tech", "Computer Science & Engineering", 120), ("UG", "B.Tech", "Electronics & Communication Engineering", 60),
             ("UG", "B.Tech", "Mechanical Engineering", 60)],
    "nvie": [("UG", "B.Tech", "Computer Science & Engineering", 120), ("UG", "B.Tech", "Mechanical Engineering", 60),
             ("UG", "B.Tech", "Civil Engineering", 60)],
}
DEPTS = {
    "piat": ["Computer Engineering", "Information Technology", "E&TC Engineering", "Mechanical Engineering", "Applied Sciences"],
    "apex": ["Computer Science & Engineering", "Electronics & Communication", "Mechanical Engineering", "Applied Sciences"],
    "nvie": ["Computer Science & Engineering", "Mechanical Engineering", "Civil Engineering", "Applied Sciences"],
}


class Dataset:
    def __init__(self):
        self.auth: dict[str, list] = {k: [] for k in ["digilocker", "nba", "naac", "municipal_fire", "land_records",
                                                       "ter_payments", "aicte_eoa", "ca_udin"]}
        self.docs: dict[str, dict] = {}     # path -> document entry (docType, expectedVerification, groundTruth)

    def add_auth(self, source, ref, fields, status="VALID", doc_type=None, simulate=None, message=None, remarks=None):
        rec = {"referenceNo": ref, "docType": doc_type, "fields": fields, "status": status}
        if simulate:
            rec["simulate"] = simulate
        if message:
            rec["message"] = message
        if remarks:
            rec["remarks"] = remarks
        self.auth[source].append(rec)

    def add_doc(self, rel, doc_type, fields, expected, tampered=False, notes=None, qr_mode=None):
        self.docs[rel] = {"path": rel, "docType": doc_type, "expectedVerification": expected,
                          "groundTruth": {"docType": doc_type, "fields": fields, "tampered": tampered,
                                          **({"tamperNotes": notes} if notes else {}), **({"qr": qr_mode} if qr_mode else {})}}

    def ref(self, rel, declared=None):
        d = dict(self.docs[rel])
        if declared:
            d["docType"] = declared
        return d


DS = Dataset()


def out(rel) -> Path:
    p = SAMPLES / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# ============================================================================= document builders
def eoa_letter(inst, ref, date_iso, ay, intake, region_office, rel):
    i = INST[inst]
    progs = "; ".join(f"{p[1]} {p[2]} ({p[3]})" for p in PROGRAMMES[inst])
    claims = {"docType": "PREVIOUS_EOA_LETTER", "referenceNo": ref, "institutionName": i["name"], "permanentId": i["permanentId"],
              "academicYear": ay, "totalIntake": intake, "issueDate": date_iso}
    spec = R.DocSpec(
        authority="All India Council for Technical Education", authority_sub=[
            f"{region_office} Regional Office  |  Approval Bureau", "(Simulated specimen of an approval letter - fictional data)"],
        title=f"EXTENSION OF APPROVAL FOR THE ACADEMIC YEAR {ay}", ref_label="F.No.", ref=ref, date_label="Date",
        date_text=dmy(date_iso), to_lines=["To,", "The Principal / Director", i["name"], i["address"]],
        subject=f"Extension of Approval (EoA) for the Academic Year {ay} - reg.",
        paras_before=[f"With reference to the online application submitted under the Approval Process Handbook, the Council is "
                      f"pleased to accord Extension of Approval to the institution for the Academic Year {ay} subject to the "
                      f"conditions stated herein."],
        kv=[("Name of the Institution", i["name"]), ("Permanent ID", i["permanentId"]), ("Academic Year", ay),
            ("Total Approved Intake", str(intake)), ("Programmes / Intake", progs), ("Approval Status", "Approved (EoA)")],
        paras_after=["The institution shall comply with all norms and maintain the infrastructure, faculty and other "
                     "requirements throughout the approval period. Any misrepresentation shall attract action as per Regulations."],
        sign=["", "(Approval Officer)", f"{region_office} Regional Office"], qr_payload=qr("aicte-approvals", claims))
    R.make_pdf(out(rel), spec, "AICTE Approval Portal - Letter Service (simulated)", dt(date_iso))
    DS.add_auth("aicte_eoa", ref, {"institutionName": i["name"], "permanentId": i["permanentId"], "academicYear": ay,
                                   "totalIntake": intake, "issueDate": date_iso}, doc_type="PREVIOUS_EOA_LETTER")
    DS.add_doc(rel, "PREVIOUS_EOA_LETTER", {"referenceNo": ref, "institutionName": i["name"], "issueDate": date_iso,
                                            "permanentId": i["permanentId"], "academicYear": ay, "totalIntake": intake},
               "VERIFIED", qr_mode="valid")


def fire_noc(inst, kid, authority, sub, ref, issue, expiry, rel, expected="VERIFIED", status="VALID"):
    i = INST[inst]
    claims = {"docType": "FIRE_NOC", "referenceNo": ref, "institutionName": i["name"], "issueDate": issue, "expiryDate": expiry}
    spec = R.DocSpec(
        authority=authority, authority_sub=sub, title="FIRE SAFETY NO OBJECTION CERTIFICATE (RENEWAL)",
        ref_label="NOC No.", ref=ref, date_label="Date of Issue", date_text=dmy(issue),
        paras_before=["On the basis of the inspection carried out by the Fire Officer and the compliance report submitted, "
                      "No Objection Certificate is hereby granted from the fire safety point of view for the premises described below."],
        kv=[("Name of the Institution", i["name"]), ("Premises", "Academic Blocks A-D, Library, Workshop & Hostel H1"),
            ("Address", i["address"]), ("Occupancy Type", "Educational (Group B)"), ("Building Height", "17.5 m"),
            ("Fire Installations", "Hydrant system, sprinklers, fire alarm, 64 extinguishers"),
            ("Valid up to", dmy(expiry))],
        paras_after=["This certificate is valid subject to the fire-fighting installations being maintained in working order. "
                     "The owner/occupier shall apply for renewal before expiry."],
        sign=["", "Chief Fire Officer", authority.split(" (")[0]], qr_payload=qr(kid, claims), stamp_text="CHIEF FIRE OFFICER  SIMULATED SEAL")
    R.make_pdf(out(rel), spec, "e-NOC Fire Services Portal (simulated)", dt(issue))
    DS.add_auth("municipal_fire", ref, {"institutionName": i["name"], "issueDate": issue, "expiryDate": expiry}, status=status, doc_type="FIRE_NOC")
    DS.add_doc(rel, "FIRE_NOC", {"referenceNo": ref, "institutionName": i["name"], "issueDate": issue, "expiryDate": expiry},
               expected, qr_mode="valid")


def occupancy(inst, kid, authority, ref, issue, area, rel, date_style="long"):
    i = INST[inst]
    claims = {"docType": "OCCUPANCY_CERTIFICATE", "referenceNo": ref, "institutionName": i["name"], "issueDate": issue, "builtUpAreaSqm": area}
    spec = R.DocSpec(
        authority=authority, authority_sub=["Building Permission Cell  |  (Simulated urban local body)", f"{i['city']}, {i['state']}"],
        title="OCCUPANCY CERTIFICATE", ref_label="OC No.", ref=ref, date_label="Date", date_text=dmy(issue, date_style),
        paras_before=["Certified that the buildings described below have been completed in accordance with the approved drawings and "
                      "are fit for occupation for educational use. Permission to occupy is hereby granted."],
        kv=[("Name of the Institution", i["name"]), ("Owner", i["trustName"]), ("Site Address", i["address"]),
            ("Total Built-up Area", f"{area:,} sq.m"), ("Use", "Educational - Technical Institution"), ("No. of Floors", "G + 4")],
        sign=["", "Executive Engineer", "Building Permission Cell"], qr_payload=qr(kid, claims))
    R.make_pdf(out(rel), spec, "Online Building Permission System (simulated)", dt(issue))
    DS.add_auth("municipal_fire", ref, {"institutionName": i["name"], "issueDate": issue, "builtUpAreaSqm": area}, doc_type="OCCUPANCY_CERTIFICATE")
    DS.add_doc(rel, "OCCUPANCY_CERTIFICATE", {"referenceNo": ref, "institutionName": i["name"], "issueDate": issue, "builtUpAreaSqm": area},
               "VERIFIED", qr_mode="valid")


def building_plan(inst, kid, authority, ref, issue, area_printed, rel, area_true=None, forged=False, expected="VERIFIED"):
    i = INST[inst]
    area_true = area_true or area_printed
    shown = {"docType": "BUILDING_PLAN_APPROVAL", "referenceNo": ref, "institutionName": i["name"], "issueDate": issue, "builtUpAreaSqm": area_printed}
    if forged:
        payload = forged_qr(kid, {**shown, "builtUpAreaSqm": area_true}, shown)
    else:
        payload = qr(kid, shown)
    spec = R.DocSpec(
        authority=authority, authority_sub=["Town Planning & Building Permission  |  (Simulated planning authority)", f"{i['city']}, {i['state']}"],
        title="APPROVAL OF BUILDING PLANS AND COMMENCEMENT CERTIFICATE", ref_label="Permit No.", ref=ref,
        date_label="Date", date_text=dmy(issue),
        paras_before=["Permission is hereby granted under the applicable Development Control Regulations to carry out the "
                      "construction as per the building plans submitted, subject to the conditions below."],
        kv=[("Name of the Institution", i["name"]), ("Applicant", i["trustName"]), ("Site", i["address"]),
            ("Total Built-up Area", f"{area_printed:,} sq.m"), ("Permissible FSI", "1.00"), ("Building Use", "Educational")],
        paras_after=["The commencement certificate is valid for the construction shown on the sanctioned plan. Any deviation requires revised approval."],
        sign=["", "Town Planning Officer", authority.split(" (")[0]], qr_payload=payload)
    R.make_pdf(out(rel), spec, "Online Building Permission System (simulated)", dt(issue))
    DS.add_auth("municipal_fire", ref, {"institutionName": i["name"], "issueDate": issue, "builtUpAreaSqm": area_true}, doc_type="BUILDING_PLAN_APPROVAL")
    DS.add_doc(rel, "BUILDING_PLAN_APPROVAL", {"referenceNo": ref, "institutionName": i["name"], "issueDate": issue, "builtUpAreaSqm": area_printed},
               expected, tampered=forged, notes="QR claims edited after signing (signature invalid); printed built-up area inflated" if forged else None,
               qr_mode="forged" if forged else "valid")


def land_deed(inst, office, sub, ref, issue, survey, area, village, taluka, district, vendor, rel):
    i = INST[inst]
    spec = R.DocSpec(
        authority=office, authority_sub=sub, title="CERTIFIED COPY - REGISTERED SALE DEED (EXTRACT)",
        ref_label="Registration No.", ref=ref, date_label="Date of Registration", date_text=dmy(issue),
        paras_before=["This is to certify that the following extract is a true copy of the particulars of the sale deed "
                      "registered in this office in Book No. I."],
        kv=[("Vendor", vendor), ("Purchaser", i["trustName"]), ("Survey No.", survey), ("Village", village),
            ("Taluka", taluka), ("District", district), ("Total Area", f"{area:.2f} Acres"), ("Nature of Holding", "Freehold"),
            ("Consideration", "As recorded in the registered deed")],
        paras_after=["Certified copy issued on application. Stamp duty and registration fee paid as per the Stamp Act."],
        sign=["", "Sub-Registrar", office.replace("Office of the ", "")], stamp_text="SUB-REGISTRAR  SIMULATED SEAL")
    R.make_pdf(out(rel), spec, "e-Registration Certified Copy Service (simulated)", dt(issue, 15))
    DS.add_auth("land_records", ref, {"ownerName": i["trustName"], "surveyNo": survey, "landAreaAcres": area, "village": village,
                                      "district": district, "issueDate": issue}, doc_type="LAND_DOCUMENT")
    DS.add_doc(rel, "LAND_DOCUMENT", {"referenceNo": ref, "issueDate": issue, "surveyNo": survey, "landAreaAcres": area,
                                      "ownerName": i["trustName"], "village": village, "district": district}, "VERIFIED")


def university_letter(inst, kid, univ, ref, issue, title, kv_extra, rel, with_qr=True, expected="VERIFIED", simulate=None,
                      message=None, claims_extra=None, gt_extra=None, body=None):
    i = INST[inst]
    kv = [("Name of the Institution", i["name"]), ("Academic Year", AY)] + kv_extra
    claims = {"docType": "UNIVERSITY_AFFILIATION", "referenceNo": ref, "institutionName": i["name"], "academicYear": AY,
              "issueDate": issue, **(claims_extra or {})}
    spec = R.DocSpec(
        authority=univ, authority_sub=["Office of the Registrar  |  Affiliation Section", "(Simulated affiliating university)"],
        title=title, ref_label="Letter No.", ref=ref, date_label="Date", date_text=dmy(issue),
        to_lines=["To,", "The Principal", i["name"]],
        paras_before=[body or "With reference to your application, the University, on the recommendation of the Local Inquiry "
                      "Committee and the decision of the Academic Council, conveys its decision on affiliation as below."],
        kv=kv, paras_after=["This affiliation is subject to the conditions prescribed by the University and the approval of AICTE."],
        sign=["", "Registrar", univ.split(" (")[0]], qr_payload=qr(kid, claims) if with_qr else None)
    R.make_pdf(out(rel), spec, "University ERP - Affiliation Module (simulated)", dt(issue))
    fields = {"institutionName": i["name"], "academicYear": AY, "university": univ.split(" (")[0], **(claims_extra or {})}
    DS.add_auth("digilocker", ref, fields, doc_type="UNIVERSITY_AFFILIATION", simulate=simulate, message=message)
    DS.add_doc(rel, "UNIVERSITY_AFFILIATION", {"referenceNo": ref, "institutionName": i["name"], "issueDate": issue,
                                               "academicYear": AY, **(gt_extra or {})}, expected, qr_mode="valid" if with_qr else None)


def state_noc(inst, authority, sub, ref, issue, kv_extra, rel, kid=None, scanned=False, expected="VERIFIED", simulate=None,
              message=None, fields_extra=None, title="NO OBJECTION CERTIFICATE"):
    i = INST[inst]
    claims = {"docType": "STATE_GOVT_NOC", "referenceNo": ref, "institutionName": i["name"], "academicYear": AY, "issueDate": issue,
              **(fields_extra or {})}
    spec = R.DocSpec(
        authority=authority, authority_sub=sub, title=title, ref_label="NOC No.", ref=ref, date_label="Date", date_text=dmy(issue, "dot"),
        to_lines=["To,", "The Member Secretary, AICTE (through the institution)"],
        paras_before=["The State Government has examined the proposal of the institution and has No Objection to the proposal "
                      "described below, subject to approval of the All India Council for Technical Education."],
        kv=[("Name of the Institution", i["name"]), ("Academic Year", AY)] + kv_extra,
        sign=["", "Joint Director", authority.split(",")[0]], qr_payload=qr(kid, claims) if kid else None,
        stamp_text="GOVT OF STATE  SIMULATED SEAL")
    p = out(rel)
    if scanned:
        tmp = p.with_suffix(".src.pdf")
        R.make_pdf(tmp, spec, "x", dt(issue))
        img = R.scan_effect(R.render_page(tmp, 150), seed=len(rel))
        tmp.unlink()
        R.scanned_pdf(img, p, "ScanToPDF 2.4 (office MFP)", dt(issue, 16, 30))
    else:
        R.make_pdf(p, spec, "State e-Office (simulated)", dt(issue))
    DS.add_auth("digilocker", ref, {"institutionName": i["name"], "academicYear": AY, **(fields_extra or {})}, doc_type="STATE_GOVT_NOC",
                simulate=simulate, message=message)
    DS.add_doc(rel, "STATE_GOVT_NOC", {"referenceNo": ref, "institutionName": i["name"], "issueDate": issue, "academicYear": AY,
                                       **(fields_extra or {})}, expected, qr_mode="valid" if kid else None)


def nba_cert(inst, ref, issue, programme, vfrom, vto, rel, qr_claims=None, expected="VERIFIED"):
    i = INST[inst]
    printed = {"docType": "NBA_ACCREDITATION", "referenceNo": ref, "institutionName": i["name"], "programme": programme,
               "validFrom": vfrom, "expiryDate": vto, "issueDate": issue}
    spec = R.DocSpec(
        authority="National Accreditation Board for Engineering Programmes",
        authority_sub=["(Simulated NBA-equivalent programme accreditation body)", "Accreditation Bhawan, New Delhi (fictional)"],
        title="CERTIFICATE OF PROGRAMME ACCREDITATION", ref_label="Accreditation Ref.", ref=ref, date_label="Date",
        date_text=dmy(issue),
        paras_before=["This is to certify that the undergraduate engineering programme mentioned below, offered by the institution, "
                      "has been accredited under the outcome-based accreditation framework (Tier II)."],
        kv=[("Name of the Institution", i["name"]), ("Name of the Programme", programme), ("Tier", "Tier II"),
            ("Accreditation Status", "Accredited")],
        paras_after=[f"The accreditation is valid from {dmy(vfrom)} to {dmy(vto)} subject to the institution maintaining the standards."],
        sign=["", "Member Secretary", "National Accreditation Board for Engineering Programmes"],
        qr_payload=qr("nbep", qr_claims or printed))
    R.make_pdf(out(rel), spec, "Accreditation Management System (simulated)", dt(issue))
    if not qr_claims:
        DS.add_auth("nba", ref, {"institutionName": i["name"], "programme": programme, "validFrom": vfrom, "expiryDate": vto}, doc_type="NBA_ACCREDITATION")
    DS.add_doc(rel, "NBA_ACCREDITATION", {"referenceNo": ref, "institutionName": i["name"], "issueDate": issue, "programme": programme,
                                          "validFrom": vfrom, "expiryDate": vto}, expected, tampered=bool(qr_claims),
               notes="Printed programme/validity altered; issuer-signed QR (transplanted from an older certificate) shows the original values" if qr_claims else None,
               qr_mode="mismatch" if qr_claims else "valid")


def naac_cert(inst, ref, issue, grade, cgpa, vfrom, vto, rel, with_qr=False, expected="VERIFIED", status="VALID"):
    i = INST[inst]
    claims = {"docType": "NAAC_ACCREDITATION", "referenceNo": ref, "institutionName": i["name"], "grade": grade, "cgpa": cgpa,
              "expiryDate": vto, "issueDate": issue}
    spec = R.DocSpec(
        authority="National Institutional Assessment Council",
        authority_sub=["(Simulated NAAC-equivalent assessment and accreditation body)", "Bengaluru (fictional)"],
        title="CERTIFICATE OF INSTITUTIONAL ACCREDITATION", ref_label="EC No.", ref=ref, date_label="Date", date_text=dmy(issue),
        paras_before=[f"The Executive Committee is pleased to declare {i['name']}, {i['city']} as accredited with a CGPA of "
                      f"{cgpa:.2f} on a four point scale at {grade} grade, valid from {dmy(vfrom)} to {dmy(vto)}."],
        kv=[("Name of the Institution", i["name"]), ("Cycle", "2"), ("Grade", grade), ("CGPA", f"{cgpa:.2f}")],
        sign=["", "Director", "National Institutional Assessment Council"], qr_payload=qr("niac", claims) if with_qr else None)
    R.make_pdf(out(rel), spec, "Assessment Portal (simulated)", dt(issue))
    DS.add_auth("naac", ref, {"institutionName": i["name"], "grade": grade, "cgpa": cgpa, "validFrom": vfrom, "expiryDate": vto},
                status=status, doc_type="NAAC_ACCREDITATION")
    DS.add_doc(rel, "NAAC_ACCREDITATION", {"referenceNo": ref, "institutionName": i["name"], "issueDate": issue, "grade": grade,
                                           "cgpa": cgpa, "validFrom": vfrom, "expiryDate": vto}, expected, qr_mode="valid" if with_qr else None)


def ter_receipt(inst, txn, app_no, amount, pay_iso, time_s, status_text, rel, expected="VERIFIED", simulate=None, message=None):
    i = INST[inst]
    spec = R.DocSpec(
        authority="AICTE Online Payment Gateway", authority_sub=["Total Expenditure Recovery (TER) / Processing Fee", "(Simulated payment gateway e-receipt)"],
        title="e-RECEIPT: TER / PROCESSING FEE PAYMENT",
        kv=[("Transaction ID", txn), ("Application No.", app_no), ("Name of the Institution", i["name"]),
            ("Permanent ID", i["permanentId"]), ("Academic Year", AY), ("Amount Paid", inr(amount)),
            ("Payment Date", f"{dmy(pay_iso, 'dash')} {time_s}"), ("Payment Mode", "Net Banking"), ("Transaction Status", status_text)],
        paras_after=["This is a system generated receipt. Payment is subject to realisation and reconciliation with the bank."],
        sign=["", "Accounts Section (auto-generated)"])
    R.make_pdf(out(rel), spec, "Payment Gateway Receipt Service (simulated)", dt(pay_iso, 14, 30))
    DS.add_auth("ter_payments", txn, {"amount": amount, "applicationNo": app_no, "issueDate": pay_iso,
                                      "institutionName": i["name"], "paymentStatus": "SUCCESS" if not simulate else "PENDING"},
                doc_type="TER_PAYMENT_RECEIPT", simulate=simulate, message=message)
    DS.add_doc(rel, "TER_PAYMENT_RECEIPT", {"referenceNo": txn, "institutionName": i["name"], "issueDate": pay_iso, "amount": amount,
                                            "applicationNo": app_no, "academicYear": AY}, expected)


def audit_statement(inst, firm, frn, membership, udin, fy, income, expense, rel, in_registry=True, expected="VERIFIED"):
    i = INST[inst]
    spec = R.DocSpec(
        authority=firm, authority_sub=[f"Chartered Accountants  |  FRN {frn}  (fictional firm)", f"{i['city']}"],
        title="INDEPENDENT AUDITOR'S REPORT AND SUMMARY BALANCE SHEET",
        paras_before=[f"We have audited the accompanying financial statements of {i['trustName']} in respect of {i['name']}, "
                      f"comprising the Balance Sheet as at 31st March and the Income and Expenditure Account for the Financial Year {fy}."],
        kv=[("Name of the Institution", i["name"]), ("Financial Year", fy), ("Total Income", inr(income)),
            ("Total Expenditure", inr(expense)), ("Surplus", inr(income - expense)), ("UDIN", udin),
            ("Membership No.", membership)],
        paras_after=["In our opinion the financial statements give a true and fair view in conformity with the accounting principles "
                     "generally accepted in India."],
        sign=[f"For {firm}", "Partner", f"M. No. {membership}"])
    R.make_pdf(out(rel), spec, "Microsoft Word - Audit Report", dt("2026-08-14"), creator="Microsoft Word")
    if in_registry:
        DS.add_auth("ca_udin", udin, {"financialYear": fy, "membershipNo": membership, "institutionName": i["name"], "firm": firm},
                    doc_type="AUDITED_FINANCIAL_STATEMENT")
    DS.add_doc(rel, "AUDITED_FINANCIAL_STATEMENT", {"udin": udin, "institutionName": i["name"], "financialYear": fy,
                                                    "membershipNo": membership}, expected)


def affidavit(inst, deponent, stamp_no, issue, notarised, purpose, rel, scanned=True):
    i = INST[inst]
    spec = R.DocSpec(
        authority="NON-JUDICIAL e-STAMP", authority_sub=["Certificate of Stamp Duty (simulated e-stamp paper)", f"State: {i['state']}"],
        title="AFFIDAVIT CUM UNDERTAKING", ref_label="e-Stamp Certificate No.", ref=stamp_no, date_label="Issue Date",
        date_text=dmy(issue),
        paras_before=[f"I, {deponent}, aged 52 years, Principal of {i['name']}, {i['address']}, do hereby solemnly affirm and "
                      f"state on oath as under: (1) That the information furnished in the online application for {purpose} for the "
                      f"Academic Year {AY} is true and correct. (2) That the institution fulfils the norms of the Approval Process "
                      f"Handbook and shall abide by all Regulations. (3) That no court case or adverse order is pending against the "
                      f"institution or the {i['trustName']}."],
        kv=[("Deponent", deponent), ("Name of the Institution", i["name"]), ("Academic Year", AY), ("Notarised on", dmy(notarised))],
        paras_after=["Verified at the place stated above that the contents of this affidavit are true to my knowledge and belief.",
                     "Before me, Notary Public (Reg. No. N/SIM/4471)"],
        sign=["", "DEPONENT", deponent], stamp_text="NOTARY PUBLIC  SIMULATED SEAL")
    p = out(rel)
    if scanned:
        tmp = p.with_suffix(".src.pdf")
        R.make_pdf(tmp, spec, "x", dt(issue))
        img = R.scan_effect(R.render_page(tmp, 150), seed=len(rel) + 7, angle=-0.4)
        tmp.unlink()
        R.scanned_pdf(img, p, "ScanToPDF 2.4 (office MFP)", dt(notarised, 17))
    else:
        R.make_pdf(p, spec, "Microsoft Word - Affidavit", dt(notarised), creator="Microsoft Word")
    DS.add_doc(rel, "AFFIDAVIT_UNDERTAKING", {"referenceNo": stamp_no, "institutionName": i["name"], "issueDate": issue,
                                              "notarisedOn": notarised, "deponentName": deponent, "academicYear": AY}, "MANUAL_REVIEW_REQUIRED")


def roster_pdf(inst, rows, rel, created):
    i = INST[inst]
    header = ["S.No", "Faculty ID", "Name", "PAN", "Designation", "Qualification", "Department", "Date of Joining"]
    col_x = [30, 62, 128, 262, 340, 450, 520, 700]
    body = [[str(n + 1), r["facultyId"], r["name"], r["pan"], r["designation"], r["qualification"], r["department"],
             dmy(r["joiningDate"])] for n, r in enumerate(rows)]
    R.make_table_pdf(out(rel), [f"LIST OF TEACHING FACULTY - ACADEMIC YEAR {AY}", f"Name of the Institution: {i['name']}",
                                f"Permanent ID: {i['permanentId']}  |  {i['address']}"], header, col_x, body,
                     [f"Total Faculty: {len(rows)}"], "Institute ERP 5.2", created, ["Certified correct", "Principal / Director"])
    cad = {"professor": 0, "associateProfessor": 0, "assistantProfessor": 0}
    for r in rows:
        cad[{"Professor": "professor", "Associate Professor": "associateProfessor", "Assistant Professor": "assistantProfessor"}[r["designation"]]] += 1
    DS.add_doc(rel, "FACULTY_ROSTER", {"institutionName": i["name"], "facultyCount": len(rows), "declaredTotal": len(rows),
                                       "pans": [r["pan"] for r in rows], "cadre": cad}, "NOT_APPLICABLE")


def roster_csv(inst, rows, rel):
    i = INST[inst]
    p = out(rel)
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Faculty ID", "Name", "PAN", "Designation", "Qualification", "Department", "Date of Joining"])
        for r in rows:
            w.writerow([r["facultyId"], r["name"], r["pan"], r["designation"], r["qualification"], r["department"], dmy(r["joiningDate"])])
    cad = {"professor": 0, "associateProfessor": 0, "assistantProfessor": 0}
    for r in rows:
        cad[{"Professor": "professor", "Associate Professor": "associateProfessor", "Assistant Professor": "assistantProfessor"}[r["designation"]]] += 1
    DS.add_doc(rel, "FACULTY_ROSTER", {"facultyCount": len(rows), "pans": [r["pan"] for r in rows], "cadre": cad}, "NOT_APPLICABLE")


def floor_plan(inst, architect, drawing_no, issue, total, rooms, rel):
    i = INST[inst]
    spec = R.DocSpec(
        authority=architect, authority_sub=["Licensed Architect  |  Council of Architecture Reg. CA/2009/45512 (fictional)"],
        title="AREA STATEMENT AND FLOOR PLAN SUMMARY", ref_label="Drawing No.", ref=drawing_no, date_label="Date", date_text=dmy(issue),
        paras_before=[f"Area statement of the academic building of {i['name']} prepared from the approved drawings."],
        kv=[("Name of the Institution", i["name"])] + [(k, v) for k, v in rooms] + [("Total Built-up Area", f"{total:,} sq.m")],
        sign=["", "Architect", architect.split(",")[0]])
    R.make_pdf(out(rel), spec, "AutoCAD PDF (simulated plotter)", dt(issue), creator="AutoCAD")
    DS.add_doc(rel, "FLOOR_PLAN", {"referenceNo": drawing_no, "institutionName": i["name"], "issueDate": issue, "builtUpAreaSqm": total},
               "MANUAL_REVIEW_REQUIRED")


def fdr(inst, rel):
    i = INST[inst]
    spec = R.DocSpec(
        authority="Indus Valley National Bank", authority_sub=["Waghodia Road Branch, Vadodara  |  IFSC IVNB0000412 (fictional bank)"],
        title="FIXED DEPOSIT RECEIPT - CORPUS FUND", ref_label="FDR No.", ref="IVNB/FD/0098812345", date_label="Date of Deposit",
        date_text=dmy("2026-09-05"),
        paras_before=[f"Received from {i['trustName']} for {i['name']} the sum mentioned below as a Term Deposit held in the joint "
                      f"names of the Trust and the Member Secretary, AICTE, with lien in favour of AICTE."],
        kv=[("Deposit Amount", inr(10000000)), ("Rate of Interest", "7.10 % p.a."), ("Period", "60 months"),
            ("Maturity Date", dmy("2031-09-05")), ("Maturity Value", inr(14217600))],
        sign=["", "Branch Manager", "Indus Valley National Bank"])
    R.make_pdf(out(rel), spec, "Core Banking Receipt Printer (simulated)", dt("2026-09-05"))
    DS.add_doc(rel, "CORPUS_FUND_FDR", {"referenceNo": "IVNB/FD/0098812345", "issueDate": "2026-09-05", "expiryDate": "2031-09-05",
                                        "amount": 10000000}, "MANUAL_REVIEW_REQUIRED")


def society_registration(inst, rel):
    i = INST[inst]
    ref = "MH/PUNE/F-18842/2008"
    new_name = "Pragati Institute of Technology & Research"
    spec = R.DocSpec(
        authority="Office of the Registrar of Societies & Public Trusts", authority_sub=["Pune Region  |  (Simulated registrar)"],
        title="CERTIFICATE OF REGISTRATION (AMENDED)", ref_label="Registration No.", ref=ref, date_label="Date of Amendment",
        date_text=dmy("2026-07-28"),
        paras_before=["Certified that the Society named below is registered under the Societies Registration Act, 1860 and the "
                      "Public Trusts Act, and that the amendment noted below has been recorded on the basis of the resolution of the "
                      "governing body."],
        kv=[("Name of the Society", i["trustName"]), ("Date of Registration", dmy("2008-03-14")),
            ("Amendment", "Change in name of the institution run by the Society"),
            ("Existing Name of the Institution", i["name"]), ("New Name of the Institution", new_name),
            ("Resolution dated", dmy("2026-07-12"))],
        sign=["", "Registrar of Societies", "Pune Region"])
    R.make_pdf(out(rel), spec, "Registrar e-Services (simulated)", dt("2026-07-28"))
    DS.add_auth("digilocker", ref, {"trustName": i["trustName"], "newInstitutionName": new_name, "issueDate": "2008-03-14"},
                doc_type="SOCIETY_TRUST_REGISTRATION")
    DS.add_doc(rel, "SOCIETY_TRUST_REGISTRATION", {"referenceNo": ref, "trustName": i["trustName"], "issueDate": "2008-03-14",
                                                   "newInstitutionName": new_name}, "VERIFIED")


# ============================================================================= photos
def photo(rel, img, doc_type, taken, gps, expected="NOT_APPLICABLE", software=None, exif=True, notes=None, q=86, counts=None):
    p = out(rel)
    ex = R.exif_bytes(dt(taken[:10], int(taken[11:13]), int(taken[14:16])), gps, software=software) if exif else None
    R.save_jpeg(img, p, q, ex)
    DS.add_doc(rel, doc_type, {"counts": counts or {}, "takenAt": taken if exif else None, "gps": gps if exif else None},
               expected, notes=notes)


def jitter(g, rng, m=0.0004):
    return {"lat": round(g["lat"] + rng.uniform(-m, m), 6), "lng": round(g["lng"] + rng.uniform(-m, m), 6)}


# ============================================================================= tampered land documents (apex)
def apex_land_documents():
    i = INST["apex"]
    rel = "apex/land_deed.pdf"
    ref, issue = "GN/SR/2009/7731", "2009-06-16"
    land_deed("apex", "Office of the Sub-Registrar, Greater Noida", ["Stamp & Registration Department (simulated)", "Gautam Buddh Nagar, Uttar Pradesh"],
              ref, issue, "118/2", 5.20, "Tilapta", "Dadri", "Gautam Buddh Nagar", "Shri Rampal Singh & Others", rel)
    R.tamper_pdf_incremental(SAMPLES / rel, [("118/2", "148/2"), ("5.20 Acres", "12.50 Acres")],
                             producer="Adobe Photoshop 25.1 (Windows)", mod=datetime(2026, 9, 29, 22, 41, 7))
    DS.docs[rel]["groundTruth"]["fields"].update({"surveyNo": "148/2", "landAreaAcres": 12.5})
    DS.docs[rel]["expectedVerification"] = "MISMATCH_DETECTED"
    DS.docs[rel]["groundTruth"]["tampered"] = True
    DS.docs[rel]["groundTruth"]["tamperNotes"] = ("Survey No. 118/2 -> 148/2 and area 5.20 -> 12.50 Acres re-typed in a different font "
                                                  "(Times) over redacted originals; Producer 'Adobe Photoshop'; saved as an incremental update")
    DS.docs[rel]["groundTruth"]["expectedForensicFlags"] = ["PDF_EDITING_SOFTWARE", "PDF_INCREMENTAL_UPDATE", "FONT_INCONSISTENCY", "PDF_MODIFIED_AFTER_CREATION"]

    # scanned record-of-rights extract with a pasted area value
    rel2 = "apex/land_khatauni_extract_scan.jpg"
    ref2, issue2 = "MUT/DDR/2010/1182", "2010-02-04"
    spec = R.DocSpec(
        authority="Office of the Tehsildar, Dadri", authority_sub=["Revenue Department - Record of Rights (simulated)", "Gautam Buddh Nagar, Uttar Pradesh"],
        title="KHATAUNI / RECORD OF RIGHTS - CERTIFIED EXTRACT", ref_label="Mutation Entry No.", ref=ref2,
        date_label="Date", date_text=dmy(issue2),
        paras_before=["Certified extract of the record of rights maintained under the Revenue Code for the land described below."],
        kv=[("Name of Occupant", i["trustName"]), ("Khasra No.", "118/2"), ("Village", "Tilapta"), ("Tehsil", "Dadri"),
            ("District", "Gautam Buddh Nagar"), ("Total Area", "5.20 Acres"), ("Land Use", "Institutional (converted)")],
        sign=["", "Tehsildar", "Dadri"], stamp_text="TEHSILDAR DADRI  SIMULATED SEAL")
    tmp = SAMPLES / "apex" / "_khatauni_src.pdf"
    R.make_pdf(tmp, spec, "x", dt(issue2))
    dpi = 150
    base = R.scan_effect(R.render_page(tmp, dpi), seed=91, angle=0.0)
    box = R.find_text_box(tmp, "5.20 Acres", dpi)
    tmp.unlink()
    from io import BytesIO
    from PIL import Image
    base = Image.open(BytesIO(R.jpeg_bytes(base, 72))).convert("RGB")         # original scan (q=72)
    x0, y0, x1, y1 = box
    edited = R.paste_patch(base, (x0 - 3, y0 - 3), (x1 - x0 + 40, y1 - y0 + 8), "12.50 Acres", int((y1 - y0) * 0.95))
    R.save_jpeg(edited, out(rel2), 95, R.exif_bytes(None, None, make="", model="", software="Adobe Photoshop 25.1 (Windows)"))
    DS.add_auth("land_records", ref2, {"ownerName": i["trustName"], "surveyNo": "118/2", "landAreaAcres": 5.20, "village": "Tilapta",
                                       "district": "Gautam Buddh Nagar", "issueDate": issue2}, doc_type="LAND_DOCUMENT")
    DS.add_doc(rel2, "LAND_DOCUMENT", {"referenceNo": ref2, "issueDate": issue2, "surveyNo": "118/2", "landAreaAcres": 12.5,
                                       "village": "Tilapta", "district": "Gautam Buddh Nagar"}, "MISMATCH_DETECTED", tampered=True,
               notes="Area value pasted as fresh pixels into a q72 scan and re-saved at q95 in Photoshop (EXIF Software)")
    DS.docs[rel2]["groundTruth"]["expectedForensicFlags"] = ["ELA_LOCALISED_ANOMALY", "IMAGE_EDITING_SOFTWARE"]
    DS.docs[rel2]["groundTruth"]["tamperBbox"] = [x0 - 3, y0 - 3, x1 + 37, y1 + 5]


# ============================================================================= forensic benchmark
def benchmark():
    """Clean vs tampered scans/PDFs for anomaly precision/recall (includes deliberately hard cases)."""
    from io import BytesIO
    from PIL import Image

    bdir = SAMPLES / "benchmark"
    if bdir.exists():
        shutil.rmtree(bdir)
    bdir.mkdir(parents=True)
    items = []
    sources = [p for p in sorted(DS.docs) if p.endswith(".pdf") and DS.docs[p]["docType"] in
               ("FIRE_NOC", "TER_PAYMENT_RECEIPT", "OCCUPANCY_CERTIFICATE", "LAND_DOCUMENT", "UNIVERSITY_AFFILIATION",
                "AUDITED_FINANCIAL_STATEMENT", "NAAC_ACCREDITATION", "PREVIOUS_EOA_LETTER") and not DS.docs[p]["groundTruth"]["tampered"]]
    rng = random.Random(7)
    needles = {"FIRE_NOC": "Valid up to:", "TER_PAYMENT_RECEIPT": "Amount Paid:", "OCCUPANCY_CERTIFICATE": "Total Built-up Area:",
               "LAND_DOCUMENT": "Total Area:", "UNIVERSITY_AFFILIATION": "Academic Year:", "AUDITED_FINANCIAL_STATEMENT": "Surplus:",
               "NAAC_ACCREDITATION": "CGPA:", "PREVIOUS_EOA_LETTER": "Total Approved Intake:"}
    for n, src in enumerate(sources[:8]):
        dpi = 140
        pdf = SAMPLES / src
        img = R.scan_effect(R.render_page(pdf, dpi), seed=100 + n, angle=rng.choice([-0.3, 0.2, 0.4]))
        q0 = rng.choice([70, 75, 80, 85])
        clean = bdir / f"clean_scan_{n + 1:02d}.jpg"
        R.save_jpeg(img, clean, q0)
        items.append({"path": f"benchmark/{clean.name}", "tampered": False, "kind": "scan", "notes": f"single save q{q0}"})
        # tampered variant: paste a new value right of the label
        label = needles[DS.docs[src]["docType"]]
        x0, y0, x1, y1 = R.find_text_box(pdf, label, dpi)
        base = Image.open(BytesIO(R.jpeg_bytes(img, q0))).convert("RGB")
        vx = int(256 * dpi / 72)  # value column starts 200pt right of the 56pt margin
        txt = rng.choice(["31/12/2029", "Rs. 15,00,000.00", "42,800 sq.m", "18.75 Acres", "2028-29", "Rs. 9,40,00,000.00", "3.86", "540"])
        hard = n in (3, 6)
        q1 = q0 if hard else rng.choice([92, 95])
        edited = R.paste_patch(base, (vx, y0 - 3), (int(len(txt) * (y1 - y0) * 0.62) + 10, y1 - y0 + 7), txt, int((y1 - y0) * 0.95),
                               serif=bool(n % 2))
        tam = bdir / f"tampered_scan_{n + 1:02d}.jpg"
        sw = "GIMP 2.10.36" if n in (1, 5) else None
        R.save_jpeg(edited, tam, q1, R.exif_bytes(None, None, make="", model="", software=sw) if sw else None)
        items.append({"path": f"benchmark/{tam.name}", "tampered": True, "kind": "scan",
                      "notes": f"pasted value '{txt}' then saved q{q1}" + (" (same quality as original: hard case for ELA)" if hard else "")
                               + (f"; EXIF Software {sw}" if sw else "")})
    # tampered PDFs (incremental edits)
    pdf_cases = [("Times font + Photoshop producer", "tiro", "Adobe Photoshop 25.1 (Windows)", True),
                 ("Courier font, producer unchanged", "cour", None, True),
                 ("same font (Helvetica), producer unchanged - only the incremental update remains", "helv", None, True),
                 ("full rewrite with same font and fresh metadata - hard case", "helv", None, False)]
    for n, (desc, font, producer, incremental) in enumerate(pdf_cases):
        src = sources[n]
        dst = bdir / f"tampered_pdf_{n + 1:02d}.pdf"
        shutil.copy(SAMPLES / src, dst)
        import pymupdf

        d = pymupdf.open(dst)
        page = d[0]
        label = needles[DS.docs[src]["docType"]]
        lr = page.search_for(label)[0]
        words = [w for w in page.get_text("words") if abs((w[1] + w[3]) / 2 - (lr.y0 + lr.y1) / 2) < 3 and w[0] > lr.x1 + 20]
        if not words:
            d.close()
            continue
        vr = pymupdf.Rect(min(w[0] for w in words), min(w[1] for w in words), max(w[2] for w in words), max(w[3] for w in words))
        page.add_redact_annot(vr, fill=(1, 1, 1))
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)
        page.insert_text((vr.x0, vr.y1 - 2.2), rng.choice(["31/12/2029", "Rs. 15,00,000.00", "42,800 sq.m"]), fontname=font, fontsize=9.6)
        md = d.metadata
        if producer:
            md["producer"] = producer
        if incremental:
            md["modDate"] = "D:20260930101500+05'30'"
            d.set_metadata(md)
            d.saveIncr()
            d.close()
        else:
            md["modDate"] = md.get("creationDate")
            d.set_metadata(md)
            tmp = dst.with_suffix(".tmp")
            d.save(tmp, garbage=3, deflate=True)
            d.close()
            tmp.replace(dst)
        items.append({"path": f"benchmark/{dst.name}", "tampered": True, "kind": "pdf", "notes": desc})
    return items


# ============================================================================= main
def main():
    ensure_keys()
    for inst in INST:
        d = SAMPLES / inst
        if d.exists():
            shutil.rmtree(d)
    rng = random.Random(2026)

    # ---------------- faculty
    nvie_fac = make_faculty(11, 52, "NVIE", DEPTS["nvie"])
    piat_all = make_faculty(22, 49, "PIAT", DEPTS["piat"])
    piat_roster = piat_all[:47]                       # 2 faculty in AICTE records have left (not on roster)
    apex_own = make_faculty(33, 55, "AVIT", DEPTS["apex"])
    ghost = [dict(r, facultyId=f"AVIT-{1100 + k}") for k, r in enumerate(piat_roster[10:13])]   # same people/PAN as PIAT
    apex_roster = apex_own + ghost

    # ================= NVIE (clean)
    eoa_letter("nvie", "WRO/1-1029482233/2026/EOA", "2026-05-28", "2026-27", 240, "Western", "nvie/eoa_letter_2026-27.pdf")
    fire_noc("nvie", "fire-vuf", "Vadodara Urban Fire Safety Directorate", ["(Simulated municipal fire authority)", "Fire Station Road, Raopura, Vadodara - 390001"],
             "VUFSD/NOC/2026/0718", "2026-07-14", "2027-07-13", "nvie/fire_noc.pdf")
    occupancy("nvie", "bpc-vmda", "Vadodara Metropolitan Development Authority", "VMDA/OC/2014/2231", "2014-03-12", 21450, "nvie/occupancy_certificate.pdf")
    building_plan("nvie", "bpc-vmda", "Vadodara Metropolitan Development Authority", "VMDA/BP/2012/0897", "2012-09-05", 21450, "nvie/building_plan_approval.pdf")
    land_deed("nvie", "Office of the Sub-Registrar, Vadodara-II", ["Revenue Department (simulated)", "Vadodara, Gujarat"], "VDR-II/4471/2005",
              "2005-11-21", "211/2", 15.40, "Waghodia", "Waghodia", "Vadodara", "Shri Ramanbhai K. Patel", "nvie/land_sale_deed.pdf")
    university_letter("nvie", "univ-ntu", "Narmada Technological University", "NTU/AFF/2026/1187", "2026-08-02",
                      "CONTINUATION OF AFFILIATION", [("Nature of Affiliation", "Continuation (Permanent)"), ("Total Intake", "240")],
                      "nvie/university_affiliation_2027-28.pdf", claims_extra={"totalIntake": 240}, gt_extra={"totalIntake": 240})
    nba_cert("nvie", "NBEP/2025/NV/0233", "2025-06-20", "B.Tech Computer Science & Engineering", "2025-07-01", "2028-06-30", "nvie/nba_accreditation_cse.pdf")
    naac_cert("nvie", "NIAC/EC/2024/118/A", "2024-02-15", "A+", 3.31, "2024-02-15", "2029-02-14", "nvie/naac_certificate.pdf")
    ter_receipt("nvie", "TERX2026091800417", "APP-2027-WR-10294", 150000, "2026-09-18", "14:22:51", "SUCCESS", "nvie/ter_receipt_eoa.pdf")
    roster_csv("nvie", nvie_fac, "nvie/faculty_roster.csv")
    audit_statement("nvie", "M/s Shah Mehta & Co.", "118842W", "104377", "26104377BKQXWE7781", "2025-26", 184260000, 169510000,
                    "nvie/audited_financial_statement_2025-26.pdf")
    affidavit("nvie", "Dr. Hemant R. Desai", "IN-GJ-SIM-26-0045512", "2026-09-10", "2026-09-11", "Extension of Approval",
              "nvie/affidavit_eoa_2027-28.pdf", scanned=True)
    g = INST["nvie"]["campusGps"]
    photo("nvie/photos/classroom_204.jpg", R.scene_classroom(30, 101), "INFRA_PHOTO_CLASSROOM", "2026-09-12T10:41:00", jitter(g, rng),
          counts={"desks": 30, "seatsEstimated": 60})
    photo("nvie/photos/computer_lab_2.jpg", R.scene_computer_lab(30, 102), "INFRA_PHOTO_COMPUTER_LAB", "2026-09-12T11:05:00", jitter(g, rng),
          counts={"monitors": 30})
    photo("nvie/photos/library.jpg", R.scene_library(5, 103), "INFRA_PHOTO_LIBRARY", "2026-09-12T11:30:00", jitter(g, rng), counts={"bookcases": 5})
    photo("nvie/photos/ramp_block_a.jpg", R.scene_ramp(104), "INFRA_PHOTO_ACCESSIBILITY", "2026-09-12T12:02:00", jitter(g, rng), counts={"rampHandrails": 2})
    # new course (AI & DS)
    university_letter("nvie", "univ-ntu", "Narmada Technological University", "NTU/AFF/NC/2026/0142", "2026-09-25",
                      "CONSENT OF AFFILIATION FOR NEW COURSE (PROVISIONAL)",
                      [("Course", "B.Tech Artificial Intelligence & Data Science"), ("Total Intake", "60"),
                       ("Nature of Affiliation", "Provisional (new course)")], "nvie/new_course/university_consent_ai_ds.pdf",
                      with_qr=False, expected="VERIFICATION_PENDING", simulate="PENDING",
                      message="Issuer (Narmada Technological University) has not yet pushed this document to DigiLocker; request queued for issuer consent",
                      claims_extra={"course": "B.Tech Artificial Intelligence & Data Science", "totalIntake": 60},
                      gt_extra={"course": "B.Tech Artificial Intelligence & Data Science", "totalIntake": 60})
    state_noc("nvie", "Commissionerate of Technical Education, Gujarat", ["Government of Gujarat  |  (Simulated State department)", "Gandhinagar"],
              "CTE/NOC/2026/3381", "2026-09-30", [("Course", "B.Tech Artificial Intelligence & Data Science"), ("Intake", "60")],
              "nvie/new_course/state_noc_ai_ds_scan.pdf", scanned=True, expected="SOURCE_UNAVAILABLE", simulate="OUTAGE",
              message="Issuer endpoint of the Commissionerate of Technical Education (Gujarat) is not responding (simulated outage)",
              fields_extra={"course": "B.Tech Artificial Intelligence & Data Science"},
              title="NO OBJECTION CERTIFICATE FOR INTRODUCTION OF NEW COURSE")
    fdr("nvie", "nvie/new_course/corpus_fund_fdr.pdf")
    floor_plan("nvie", "Ar. Kavita Joshi, Licensed Architect", "KJA/NVIE/2026/07", "2026-08-20", 2640,
               [("Ground Floor", "Classrooms 2 x 72 sq.m, AI & DS Lab 1 (132 sq.m)"), ("First Floor", "Classrooms 2 x 72 sq.m, Data Lab (132 sq.m)"),
                ("Second Floor", "Project Lab (110 sq.m), Faculty rooms, Seminar Hall (180 sq.m)"), ("No. of Floors", "3"),
                ("Classrooms", "4"), ("Laboratories", "3")], "nvie/new_course/floor_plan_ai_ds_block.pdf")
    photo("nvie/new_course/ai_ds_lab.jpg", R.scene_laboratory(3, 2, 105, sign="AI & DATA SCIENCE LAB"), "INFRA_PHOTO_LABORATORY",
          "2026-09-26T15:12:00", jitter(g, rng), counts={"workbenches": 3, "fireExtinguishers": 2})
    ter_receipt("nvie", "TERX2026100200981", "APP-2027-WR-10377", 100000, "2026-10-02", "11:08:40", "SUCCESS", "nvie/new_course/ter_receipt_new_course.pdf")
    affidavit("nvie", "Dr. Hemant R. Desai", "IN-GJ-SIM-26-0047730", "2026-10-01", "2026-10-03", "Introduction of a New Course",
              "nvie/new_course/affidavit_new_course.pdf", scanned=False)

    # ================= PIAT (deficiencies) + change of name
    eoa_letter("piat", "WRO/1-3948291012/2026/EOA", "2026-05-30", "2026-27", 300, "Western", "piat/eoa_letter_2026-27.pdf")
    fire_noc("piat", "fire-pmr", "Pune Metropolitan Region Fire & Emergency Services", ["(Simulated municipal fire authority)", "Central Fire Station, Pune - 411002"],
             "PMRFES/NOC/2025/1093", "2025-10-11", "2026-10-10", "piat/fire_noc.pdf", expected="EXPIRED", status="EXPIRED")
    occupancy("piat", "bpc-pmr", "Pune Metropolitan Region Development Authority", "PMRDA/OC/2011/0457", "2011-08-18", 26800, "piat/occupancy_certificate.pdf")
    roster_pdf("piat", piat_roster, "piat/faculty_roster.pdf", dt("2026-09-20"))
    university_letter("piat", "univ-stu", "Sahyadri Technological University", "STU/AFF/2026/2240", "2026-08-08",
                      "CONTINUATION OF AFFILIATION", [("Nature of Affiliation", "Continuation (Permanent)"), ("Total Intake", "300")],
                      "piat/university_affiliation_2027-28.pdf", claims_extra={"totalIntake": 300}, gt_extra={"totalIntake": 300})
    nba_cert("piat", "NBEP/2024/PI/0377", "2024-06-24", "B.Tech Computer Engineering", "2024-07-01", "2027-06-30", "piat/nba_accreditation_ce.pdf")
    ter_receipt("piat", "TERX2026101500112", "APP-2027-WR-10511", 150000, "2026-10-15", "18:47:02", "PENDING (awaiting bank confirmation)",
                "piat/ter_receipt_eoa.pdf", expected="VERIFICATION_PENDING", simulate="PENDING",
                message="Gateway reports the transaction as initiated; settlement confirmation from the bank is awaited")
    audit_statement("piat", "M/s Deshpande Kulkarni & Associates", "121907W", "112840", "26112840BMTRQP4410", "2025-26", 231450000, 219870000,
                    "piat/audited_financial_statement_2025-26.pdf")
    affidavit("piat", "Dr. Sunil V. Gokhale", "IN-MH-SIM-26-0193377", "2026-09-22", "2026-09-23", "Extension of Approval",
              "piat/affidavit_eoa_2027-28.pdf", scanned=True)
    gp = INST["piat"]["campusGps"]
    photo("piat/photos/computer_lab_1.jpg", R.scene_computer_lab(38, 201, sign="COMPUTER LAB - 1"), "INFRA_PHOTO_COMPUTER_LAB",
          "2026-09-18T12:15:00", jitter(gp, rng), counts={"monitors": 38})
    photo("piat/photos/classroom_105.jpg", R.scene_classroom(30, 202, sign="CLASSROOM 105"), "INFRA_PHOTO_CLASSROOM",
          "2026-09-18T12:40:00", jitter(gp, rng), counts={"desks": 30, "seatsEstimated": 60})
    photo("piat/photos/library.jpg", R.scene_library(6, 203), "INFRA_PHOTO_LIBRARY", "2026-09-18T13:00:00", None, exif=False,
          counts={"bookcases": 6}, notes="EXIF stripped (WhatsApp-forwarded image)")
    # change of name
    society_registration("piat", "piat/change_of_name/society_registration_amended.pdf")
    university_letter("piat", "univ-stu", "Sahyadri Technological University", "STU/AFF/CN/2026/0061", "2026-09-05",
                      "NO OBJECTION FOR CHANGE IN NAME OF AFFILIATED COLLEGE",
                      [("Proposed Name", "Pragati Institute of Technology & Research"), ("Reason", "Resolution of the governing body dated 12/07/2026")],
                      "piat/change_of_name/university_noc_name_change.pdf",
                      claims_extra={"proposedName": "Pragati Institute of Technology & Research"},
                      gt_extra={"proposedName": "Pragati Institute of Technology & Research"},
                      body="The University has No Objection to the change in name of the affiliated college as proposed below, subject to approval of AICTE.")
    state_noc("piat", "Directorate of Technical Education, Maharashtra", ["Government of Maharashtra  |  (Simulated State department)", "Mumbai"],
              "DTE/MH/NOC/2026/5521", "2026-09-19", [("Proposed Name", "Pragati Institute of Technology & Management"),
                                                     ("Proposal", "Change in name of the institution")],
              "piat/change_of_name/state_noc_name_change.pdf", kid="dte-mh",
              fields_extra={"proposedName": "Pragati Institute of Technology & Management"},
              title="NO OBJECTION CERTIFICATE FOR CHANGE IN NAME OF INSTITUTION")
    affidavit("piat", "Dr. Sunil V. Gokhale", "IN-MH-SIM-26-0201145", "2026-09-24", "2026-09-25", "Change in Name of the Institution",
              "piat/change_of_name/affidavit_name_change.pdf", scanned=False)
    ter_receipt("piat", "TERX2026092600551", "APP-2027-WR-10498", 50000, "2026-09-26", "10:02:13", "SUCCESS",
                "piat/change_of_name/ter_receipt_name_change.pdf")

    # ================= APEX (high risk) + draft EoA
    eoa_letter("apex", "NRO/1-8492048217/2026/EOA", "2026-06-02", "2026-27", 240, "Northern", "apex/eoa_letter_2026-27.pdf")
    fire_noc("apex", "fire-gn", "Greater Noida Fire & Rescue Services", ["(Simulated municipal fire authority)", "Sector Alpha-II, Greater Noida"],
             "GNFRS/NOC/2026/0264", "2026-04-21", "2027-04-20", "apex/fire_noc.pdf")
    apex_land_documents()
    nba_cert("apex", "NBEP/2024/AP/0419", "2024-06-18", "B.Tech Computer Science & Engineering", "2024-07-01", "2027-06-30",
             "apex/nba_accreditation_cse.pdf", expected="MISMATCH_DETECTED",
             qr_claims={"docType": "NBA_ACCREDITATION", "referenceNo": "NBEP/2021/AP/0127", "institutionName": INST["apex"]["name"],
                        "programme": "B.Tech Mechanical Engineering", "validFrom": "2021-07-01", "expiryDate": "2024-06-30", "issueDate": "2021-06-22"})
    DS.add_auth("nba", "NBEP/2021/AP/0127", {"institutionName": INST["apex"]["name"], "programme": "B.Tech Mechanical Engineering",
                                             "validFrom": "2021-07-01", "expiryDate": "2024-06-30"}, status="EXPIRED", doc_type="NBA_ACCREDITATION")
    building_plan("apex", "bpc-gn", "Greater Noida Urban Planning Board", "GNUPB/BP/2010/0566", "2010-01-12", 24600,
                  "apex/building_plan_approval.pdf", area_true=14600, forged=True, expected="MISMATCH_DETECTED")
    roster_pdf("apex", apex_roster, "apex/faculty_roster.pdf", dt("2026-09-28"))
    university_letter("apex", "univ-gangtu", "Gangetic Technical University", "GANGTU/AFF/2026/0912", "2026-08-21",
                      "CONSENT FOR INCREASE IN INTAKE", [("Nature of Affiliation", "Continuation with increase in intake"),
                                                         ("Programme", "B.Tech Computer Science & Engineering: 120 to 180"),
                                                         ("Total Intake", "300")],
                      "apex/university_consent_intake.pdf", claims_extra={"totalIntake": 300}, gt_extra={"totalIntake": 300})
    ter_receipt("apex", "TERX2026100800734", "APP-2027-NR-20871", 200000, "2026-10-08", "16:31:44", "SUCCESS", "apex/ter_receipt_intake.pdf")
    floor_plan("apex", "Ar. Rohit Saxena, Licensed Architect", "RSA/AVIT/2026/14", "2026-09-02", 24600,
               [("Existing Built-up Area", "14,600 sq.m"), ("Proposed Additional Block", "10,000 sq.m (claimed as constructed)"),
                ("Classrooms", "22"), ("Laboratories", "16"), ("No. of Floors", "G + 4")], "apex/floor_plan_area_statement.pdf")
    audit_statement("apex", "M/s Verma Bansal & Co.", "009812N", "131975", "26131975BHQZNM5520", "2025-26", 152300000, 149850000,
                    "apex/audited_financial_statement_2025-26.pdf", in_registry=False, expected="MISMATCH_DETECTED")
    ga = INST["apex"]["campusGps"]
    shutil.copy(SAMPLES / "nvie/photos/classroom_204.jpg", out("apex/photos/classroom_301.jpg"))
    DS.add_doc("apex/photos/classroom_301.jpg", "INFRA_PHOTO_CLASSROOM",
               {"counts": {"desks": 30, "seatsEstimated": 60}, "takenAt": DS.docs["nvie/photos/classroom_204.jpg"]["groundTruth"]["fields"]["takenAt"],
                "gps": DS.docs["nvie/photos/classroom_204.jpg"]["groundTruth"]["fields"]["gps"]}, "NOT_APPLICABLE", tampered=True,
               notes="Byte-identical copy of another institution's photo (nvie/photos/classroom_204.jpg); geo-tag ~900 km from campus")
    photo("apex/photos/computer_lab_3.jpg", R.scene_computer_lab(36, 301, sign="COMPUTER LAB - 3"), "INFRA_PHOTO_COMPUTER_LAB",
          "2023-02-14T10:20:00", jitter(ga, rng), counts={"monitors": 36}, notes="Photo taken Feb 2023 (older than 12 months)")
    lab = R.scene_laboratory(3, 1, 302, sign="ELECTRONICS LAB").filter(ImageFilter.GaussianBlur(4.5))
    photo("apex/photos/electronics_lab.jpg", lab, "INFRA_PHOTO_LABORATORY", "2026-09-27T16:45:00", jitter(ga, rng),
          counts={"workbenches": 3, "fireExtinguishers": 1}, notes="Heavily blurred")
    # draft EoA
    occupancy("apex", "bpc-gn", "Greater Noida Urban Planning Board", "GNUPB/OC/2012/0311", "2012-11-03", 14600,
              "apex/eoa_draft/occupancy_certificate.pdf", date_style="us")
    naac_cert("apex", "NIAC/EC/2020/077/B", "2020-03-31", "B++", 2.84, "2020-03-31", "2025-03-30", "apex/eoa_draft/naac_certificate.pdf",
              with_qr=True, expected="EXPIRED", status="EXPIRED")

    bench = benchmark()

    # ================= records
    def records(inst, faculty_rows, land, terp, approvals, accreditations, deficiency, affidavits):
        return {"previousApprovals": approvals,
                "approvedProgrammes": [{"level": p[0], "programme": p[1], "course": p[2], "shift": "1st", "intake": p[3]} for p in PROGRAMMES[inst]],
                "faculty": record_faculty(faculty_rows), "accreditations": accreditations, "landAndBuilding": land,
                "terPayments": terp, "deficiencyHistory": deficiency, "affidavits": affidavits}

    institutions = []
    nv = INST["nvie"]
    institutions.append({**nv, "records": records("nvie", nvie_fac,
        {"landAreaAcres": 15.4, "builtUpAreaSqm": 21450, "ownership": "Owned (freehold)", "registryRef": "VDR-II/4471/2005"},
        [{"year": "2025-26", "amount": 150000, "txnId": "TERX2025091100231", "status": "PAID", "paidOn": "2025-09-11"},
         {"year": "2026-27", "amount": 150000, "txnId": "TERX2026021900877", "status": "PAID", "paidOn": "2026-02-19"},
         {"year": "2027-28", "amount": 150000, "txnId": "TERX2026091800417", "status": "PAID", "paidOn": "2026-09-18"},
         {"year": "2027-28", "amount": 100000, "txnId": "TERX2026100200981", "status": "PAID", "paidOn": "2026-10-02"}],
        [{"year": "2024-25", "status": "APPROVED", "letterRef": "WRO/1-1029482233/2024/EOA", "date": "2024-05-24"},
         {"year": "2025-26", "status": "APPROVED", "letterRef": "WRO/1-1029482233/2025/EOA", "date": "2025-05-27"},
         {"year": "2026-27", "status": "APPROVED", "letterRef": "WRO/1-1029482233/2026/EOA", "date": "2026-05-28"}],
        [{"body": "NBA", "programme": "B.Tech Computer Science & Engineering", "grade": None, "validFrom": "2025-07-01", "validTo": "2028-06-30", "ref": "NBEP/2025/NV/0233"},
         {"body": "NAAC", "programme": None, "grade": "A+", "validFrom": "2024-02-15", "validTo": "2029-02-14", "ref": "NIAC/EC/2024/118/A"}],
        [{"year": "2024-25", "item": "Library e-journal subscription short", "status": "CLOSED"}],
        [{"year": "2026-27", "type": "EoA affidavit", "ref": "IN-GJ-SIM-25-0031180", "notarisedOn": "2026-02-10"}])})
    pi = INST["piat"]
    institutions.append({**pi, "records": records("piat", piat_all,
        {"landAreaAcres": 10.5, "builtUpAreaSqm": 26800, "ownership": "Owned (freehold)", "registryRef": "HVL-III/2231/2008"},
        [{"year": "2025-26", "amount": 150000, "txnId": "TERX2025090400118", "status": "PAID", "paidOn": "2025-09-04"},
         {"year": "2026-27", "amount": 150000, "txnId": "TERX2026022700412", "status": "PAID", "paidOn": "2026-02-27"},
         {"year": "2027-28", "amount": 150000, "txnId": "TERX2026101500112", "status": "PENDING", "paidOn": None}],
        [{"year": "2024-25", "status": "APPROVED", "letterRef": "WRO/1-3948291012/2024/EOA", "date": "2024-05-29"},
         {"year": "2025-26", "status": "APPROVED_WITH_CONDITIONS", "letterRef": "WRO/1-3948291012/2025/EOA", "date": "2025-06-03"},
         {"year": "2026-27", "status": "APPROVED", "letterRef": "WRO/1-3948291012/2026/EOA", "date": "2026-05-30"}],
        [{"body": "NBA", "programme": "B.Tech Computer Engineering", "grade": None, "validFrom": "2024-07-01", "validTo": "2027-06-30", "ref": "NBEP/2024/PI/0377"}],
        [{"year": "2025-26", "item": "Faculty-student ratio below norm (Computer Engineering)", "status": "OPEN"},
         {"year": "2024-25", "item": "Fire NOC renewal delayed", "status": "CLOSED"}],
        [{"year": "2026-27", "type": "EoA affidavit", "ref": "IN-MH-SIM-25-0170021", "notarisedOn": "2026-02-20"}])})
    ap = INST["apex"]
    institutions.append({**ap, "records": records("apex", apex_own,
        {"landAreaAcres": 5.2, "builtUpAreaSqm": 14600, "ownership": "Owned (freehold)", "registryRef": "GN/SR/2009/7731"},
        [{"year": "2025-26", "amount": 150000, "txnId": "TERX2025091500771", "status": "PAID", "paidOn": "2025-09-15"},
         {"year": "2026-27", "amount": 150000, "txnId": "TERX2026030200160", "status": "PAID", "paidOn": "2026-03-02"}],
        [{"year": "2024-25", "status": "APPROVED", "letterRef": "NRO/1-8492048217/2024/EOA", "date": "2024-06-04"},
         {"year": "2025-26", "status": "APPROVED", "letterRef": "NRO/1-8492048217/2025/EOA", "date": "2025-06-06"},
         {"year": "2026-27", "status": "APPROVED", "letterRef": "NRO/1-8492048217/2026/EOA", "date": "2026-06-02"}],
        [{"body": "NBA", "programme": "B.Tech Mechanical Engineering", "grade": None, "validFrom": "2021-07-01", "validTo": "2024-06-30", "ref": "NBEP/2021/AP/0127"},
         {"body": "NAAC", "programme": None, "grade": "B++", "validFrom": "2020-03-31", "validTo": "2025-03-30", "ref": "NIAC/EC/2020/077/B"}],
        [{"year": "2025-26", "item": "Built-up area deficit for proposed intake", "status": "OPEN"}],
        [{"year": "2026-27", "type": "EoA affidavit", "ref": "IN-UP-SIM-25-0088123", "notarisedOn": "2026-02-26"}])})

    # ================= applications
    A = []
    A.append({"key": "nvie-eoa-2027", "institutionKey": "nvie", "category": "EOA", "academicYear": AY, "status": "SUBMITTED",
              "formData": {"totalIntake": 240, "programmes": [{"course": p[2], "intake": p[3]} for p in PROGRAMMES["nvie"]],
                           "facultyCount": 52, "landAreaAcres": 15.4, "builtUpAreaSqm": 21450, "terTxnId": "TERX2026091800417",
                           "terAmount": 150000, "nbaAccredited": True, "naacAccredited": True, "computerLabTerminals": 30,
                           "classroomSeats": 60, "fireNocRef": "VUFSD/NOC/2026/0718"},
              "scenario": "Clean Extension of Approval: every document present, issuer-signed QR codes valid, all authority records match; "
                          "faculty roster consistent with AICTE records and FSR within 1:20. Expect high compliance and LOW risk. "
                          "The notarised affidavit (no issuing-authority source) is routed to MANUAL_REVIEW_REQUIRED.",
              "expectedFindings": ["VERIFICATION:AFFIDAVIT_UNDERTAKING (MANUAL_REVIEW_REQUIRED, info)"],
              "documents": [DS.ref(p) for p in ["nvie/eoa_letter_2026-27.pdf", "nvie/affidavit_eoa_2027-28.pdf", "nvie/ter_receipt_eoa.pdf",
                                                "nvie/fire_noc.pdf", "nvie/occupancy_certificate.pdf", "nvie/faculty_roster.csv",
                                                "nvie/university_affiliation_2027-28.pdf", "nvie/audited_financial_statement_2025-26.pdf",
                                                "nvie/nba_accreditation_cse.pdf", "nvie/naac_certificate.pdf", "nvie/building_plan_approval.pdf",
                                                "nvie/land_sale_deed.pdf", "nvie/photos/computer_lab_2.jpg", "nvie/photos/classroom_204.jpg",
                                                "nvie/photos/library.jpg", "nvie/photos/ramp_block_a.jpg"]]})
    A.append({"key": "piat-eoa-2027", "institutionKey": "piat", "category": "EOA", "academicYear": AY, "status": "SUBMITTED",
              "formData": {"totalIntake": 300, "programmes": [{"course": p[2], "intake": p[3]} for p in PROGRAMMES["piat"]],
                           "facultyCount": 52, "landAreaAcres": 10.5, "builtUpAreaSqm": 26800, "terTxnId": "TERX2026101500112",
                           "terAmount": 150000, "nbaAccredited": True, "naacAccredited": False, "computerLabTerminals": 40,
                           "classroomSeats": 60, "fireNocRef": "PMRFES/NOC/2025/1093"},
              "scenario": "EoA with deficiencies: Fire NOC expired on 10 Oct 2026 (16 days before the reference date); faculty count "
                          "declared 52 vs 47 on the roster vs 49 in AICTE records; FSR 1200 students / 47 faculty = 25.5 > 20; TER "
                          "payment still pending settlement; computer-lab photo shows 38 terminals against 40 declared; library photo has no EXIF.",
              "expectedFindings": ["EXPIRED_DOCUMENT:FIRE_NOC", "INCONSISTENCY:facultyCount (form 52 vs roster 47)",
                                   "RECORD_MISMATCH:facultyCount (form 52 vs records 49)", "COMPLIANCE_GAP:faculty_student_ratio (25.5 > 20)",
                                   "COMPLIANCE_GAP:TER_PAYMENT (PENDING)", "VERIFICATION:TER_PAYMENT_RECEIPT (VERIFICATION_PENDING)",
                                   "INFRASTRUCTURE:INFRA_PHOTO_COMPUTER_LAB (38 detected < 40 declared)",
                                   "INFRASTRUCTURE:INFRA_PHOTO_LIBRARY (EXIF_MISSING, minor)",
                                   "VERIFICATION:AFFIDAVIT_UNDERTAKING (MANUAL_REVIEW_REQUIRED, info)"],
              "documents": [DS.ref(p) for p in ["piat/eoa_letter_2026-27.pdf", "piat/affidavit_eoa_2027-28.pdf", "piat/ter_receipt_eoa.pdf",
                                                "piat/fire_noc.pdf", "piat/occupancy_certificate.pdf", "piat/faculty_roster.pdf",
                                                "piat/university_affiliation_2027-28.pdf", "piat/audited_financial_statement_2025-26.pdf",
                                                "piat/nba_accreditation_ce.pdf", "piat/photos/computer_lab_1.jpg",
                                                "piat/photos/classroom_105.jpg", "piat/photos/library.jpg"]]})
    A.append({"key": "apex-intake-2027", "institutionKey": "apex", "category": "INTAKE_INCREASE", "academicYear": AY, "status": "SUBMITTED",
              "formData": {"currentIntake": 240, "proposedIntake": 300, "totalIntake": 300,
                           "intakeChanges": [{"course": "Computer Science & Engineering", "from": 120, "to": 180}],
                           "facultyCount": 58, "landAreaAcres": 12.5, "builtUpAreaSqm": 24600, "terTxnId": "TERX2026100800734",
                           "terAmount": 200000, "nbaAccredited": True, "naacAccredited": False, "computerLabTerminals": 36,
                           "classroomSeats": 60},
              "scenario": "High-risk intake increase: land deed edited (survey 118/2 -> 148/2, area 5.20 -> 12.50 acres) in an editor "
                          "(Photoshop producer, incremental update, different font) and a scanned khatauni extract with a pasted area value "
                          "(ELA); NBA certificate whose issuer-signed QR is for a different, expired programme; building-plan QR whose "
                          "signature fails; UDIN not found at the registry; 3 faculty PANs also on PIAT's roster; classroom photo "
                          "identical to NVIE's and geo-tagged ~900 km away; computer-lab photo from 2023; blurred lab photo; affidavit missing.",
              "expectedFindings": ["MISSING_DOCUMENT:AFFIDAVIT_UNDERTAKING", "ANOMALY:LAND_DOCUMENT (PDF_EDITING_SOFTWARE, PDF_INCREMENTAL_UPDATE, FONT_INCONSISTENCY)",
                                   "ANOMALY:LAND_DOCUMENT (ELA_LOCALISED_ANOMALY on scan, IMAGE_EDITING_SOFTWARE)",
                                   "VERIFICATION:LAND_DOCUMENT (MISMATCH_DETECTED: surveyNo, landAreaAcres)",
                                   "RECORD_MISMATCH:landAreaAcres (form 12.5 vs records 5.2)", "RECORD_MISMATCH:builtUpAreaSqm (form 24600 vs records 14600)",
                                   "VERIFICATION:NBA_ACCREDITATION (MISMATCH_DETECTED via QR_SIGNATURE)",
                                   "VERIFICATION:BUILDING_PLAN_APPROVAL (MISMATCH_DETECTED: QR signature invalid)",
                                   "VERIFICATION:AUDITED_FINANCIAL_STATEMENT (MISMATCH_DETECTED: UDIN not found)",
                                   "DUPLICATE:FACULTY_PAN x3 (shared with piat)", "DUPLICATE:INFRA_PHOTO_CLASSROOM (same sha256 as nvie)",
                                   "INFRASTRUCTURE:INFRA_PHOTO_CLASSROOM (GPS_FAR_FROM_CAMPUS)", "INFRASTRUCTURE:INFRA_PHOTO_COMPUTER_LAB (PHOTO_TOO_OLD)",
                                   "INFRASTRUCTURE:INFRA_PHOTO_LABORATORY (LOW_QUALITY_BLUR)", "COMPLIANCE_GAP:faculty_student_ratio (1200/58 = 20.7 > 20)"],
              "documents": [DS.ref(p) for p in ["apex/eoa_letter_2026-27.pdf", "apex/ter_receipt_intake.pdf", "apex/faculty_roster.pdf",
                                                "apex/floor_plan_area_statement.pdf", "apex/fire_noc.pdf", "apex/university_consent_intake.pdf",
                                                "apex/nba_accreditation_cse.pdf", "apex/land_deed.pdf", "apex/land_khatauni_extract_scan.jpg",
                                                "apex/building_plan_approval.pdf", "apex/audited_financial_statement_2025-26.pdf",
                                                "apex/photos/computer_lab_3.jpg", "apex/photos/electronics_lab.jpg", "apex/photos/classroom_301.jpg"]]})
    A.append({"key": "nvie-newcourse-2027", "institutionKey": "nvie", "category": "NEW_COURSE", "academicYear": AY, "status": "SUBMITTED",
              "formData": {"newCourse": "B.Tech Artificial Intelligence & Data Science", "newCourseIntake": 60, "currentIntake": 240,
                           "totalIntake": 300, "facultyCount": 52, "builtUpAreaSqm": 24090, "additionalBuiltUpAreaSqm": 2640,
                           "terTxnId": "TERX2026100200981", "terAmount": 100000, "corpusFundAmount": 10000000},
              "scenario": "New course with issuing-authority edge cases: the State NOC issuer endpoint is down (SOURCE_UNAVAILABLE), the "
                          "university consent is queued at DigiLocker (VERIFICATION_PENDING), and the corpus-fund FDR / floor plan / affidavit "
                          "have no verifiable source (MANUAL_REVIEW_REQUIRED). Application should move to SOURCE_VERIFICATION_PENDING rather than fail.",
              "expectedFindings": ["VERIFICATION:STATE_GOVT_NOC (SOURCE_UNAVAILABLE)", "VERIFICATION:UNIVERSITY_AFFILIATION (VERIFICATION_PENDING)",
                                   "VERIFICATION:CORPUS_FUND_FDR (MANUAL_REVIEW_REQUIRED)", "VERIFICATION:FLOOR_PLAN (MANUAL_REVIEW_REQUIRED)",
                                   "COMPLIANCE_GAP:faculty_student_ratio (1200/52 = 23.1 > 20 after new intake)"],
              "documents": [DS.ref(p) for p in ["nvie/eoa_letter_2026-27.pdf", "nvie/new_course/university_consent_ai_ds.pdf",
                                                "nvie/faculty_roster.csv", "nvie/new_course/affidavit_new_course.pdf",
                                                "nvie/new_course/ter_receipt_new_course.pdf", "nvie/new_course/floor_plan_ai_ds_block.pdf",
                                                "nvie/new_course/ai_ds_lab.jpg", "nvie/new_course/state_noc_ai_ds_scan.pdf",
                                                "nvie/new_course/corpus_fund_fdr.pdf"]]})
    A.append({"key": "piat-name-change-2027", "institutionKey": "piat", "category": "CHANGE_OF_NAME", "academicYear": AY, "status": "SUBMITTED",
              "formData": {"currentName": pi["name"], "proposedName": "Pragati Institute of Technology & Research",
                           "reason": "Re-branding approved by the governing body (resolution dated 12/07/2026)",
                           "terTxnId": "TERX2026092600551", "terAmount": 50000},
              "scenario": "Change of name: society amendment, university NOC and TER verify cleanly, but the State Government NOC "
                          "(genuinely issued, QR valid) names 'Pragati Institute of Technology & Management' instead of the proposed "
                          "'... & Research' - a cross-document inconsistency for the officer.",
              "expectedFindings": ["INCONSISTENCY:STATE_GOVT_NOC.proposedName vs formData.proposedName",
                                   "VERIFICATION:AFFIDAVIT_UNDERTAKING (MANUAL_REVIEW_REQUIRED, info)"],
              "documents": [DS.ref(p) for p in ["piat/eoa_letter_2026-27.pdf", "piat/change_of_name/society_registration_amended.pdf",
                                                "piat/change_of_name/university_noc_name_change.pdf", "piat/change_of_name/state_noc_name_change.pdf",
                                                "piat/change_of_name/affidavit_name_change.pdf", "piat/change_of_name/ter_receipt_name_change.pdf"]]})
    A.append({"key": "apex-eoa-2027-draft", "institutionKey": "apex", "category": "EOA", "academicYear": AY, "status": "DRAFT",
              "formData": {"totalIntake": 240, "facultyCount": 55, "landAreaAcres": 5.2, "builtUpAreaSqm": 14600,
                           "nbaAccredited": False, "naacAccredited": True},
              "scenario": "Draft EoA (pre-submission compliance meter): only 4 documents uploaded; the occupancy certificate was uploaded "
                          "declared as BUILDING_PLAN_APPROVAL (classifier disagrees); NAAC accreditation expired in March 2025.",
              "expectedFindings": ["INCONSISTENCY:document type (declared BUILDING_PLAN_APPROVAL, classified OCCUPANCY_CERTIFICATE)",
                                   "EXPIRED_DOCUMENT:NAAC_ACCREDITATION", "MISSING_DOCUMENT:AFFIDAVIT_UNDERTAKING",
                                   "MISSING_DOCUMENT:TER_PAYMENT_RECEIPT", "MISSING_DOCUMENT:OCCUPANCY_CERTIFICATE",
                                   "MISSING_DOCUMENT:FACULTY_ROSTER", "MISSING_DOCUMENT:UNIVERSITY_AFFILIATION"],
              "documents": [DS.ref("apex/eoa_letter_2026-27.pdf"), DS.ref("apex/fire_noc.pdf"),
                            {**DS.ref("apex/eoa_draft/occupancy_certificate.pdf", declared="BUILDING_PLAN_APPROVAL"), "expectedVerification": "MISMATCH_DETECTED"},
                            DS.ref("apex/eoa_draft/naac_certificate.pdf")]})

    data = {
        "version": "2026.10",
        "referenceDate": REFERENCE_DATE,
        "disclaimer": "Synthetic dataset for the VeriSense SIH 2026 prototype. All institutions, authorities, people, PANs, "
                      "reference numbers and records are fictional; issuers are SIMULATED.",
        "institutions": institutions,
        "applications": A,
        "authorityRecords": DS.auth,
        "documents": sorted(DS.docs.values(), key=lambda d: d["path"]),
        "benchmark": bench,
    }
    (SAMPLES / "scenarios.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    total = sum(p.stat().st_size for p in SAMPLES.rglob("*") if p.is_file())
    print(f"documents: {len(DS.docs)}  benchmark: {len(bench)}  applications: {len(A)}  total samples size: {total / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
