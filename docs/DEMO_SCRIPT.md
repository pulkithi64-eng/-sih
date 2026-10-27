# Seven-Minute Demo Script

For SIH 2026 evaluators. Every step uses the seeded synthetic data; all passwords are `Demo@2026`.

**Before you start**

```bash
cd backend && uv run python -m seed.seed --reset      # fresh, deterministic demo data
uv run uvicorn app.main:app --port 8001
cd frontend && npm run dev                            # http://localhost:5176
```

Open three browser profiles (or private windows) so you can switch users without logging out:
`officer.wro`, `officer.nro`, `rd.wro` / `admin`.

| Seeded application | Institution (region) | Category | Shows |
|---|---|---|---|
| `piat-eoa-2027` | Pragati Institute of Advanced Technology (WR) | EoA | Expired Fire NOC, faculty mismatches, FSR breach, TER pending, infra shortfall |
| `apex-intake-2027` | Apex Valley Institute of Technology & Management (NR) | Intake increase | Land-deed tampering, QR signature failures, duplicate faculty, reused/geo-far photo |
| `nvie-eoa-2027` | Narmada Valley Institute of Engineering (WR) | EoA | Clean baseline |
| `nvie-newcourse-2027` | Narmada Valley Institute of Engineering (WR) | New course | Source unavailable, pending, manual review |
| `piat-name-change-2027` | PIAT (WR) | Change of name | Genuine NOC with a different proposed name |
| `apex-eoa-2027-draft` | Apex (NR) | EoA (draft) | Institution self-check |

Application numbers are generated at seed time; find them by institution and category in
**Applications**.

---

## 0:00 – 0:45 · The problem and the principle (website)

1. Open `http://localhost:5176/`. One sentence: *"An approval application is dozens of documents
   from many issuers; VeriSense does the preliminary cross-checking and hands the officer
   evidence — it never decides."*
2. Scroll to the pipeline diagram: steps 1–6 automated, 7–8 human.
3. Open **PS mapping** (`/compliance`) for five seconds: every PS requirement, with honest status
   (issuing authorities are simulated behind a real adapter layer).

## 0:45 – 1:30 · Institution self-check (`inst.apex`)

1. Log in as `inst.apex` → **My applications** → the **EoA draft**.
2. Click **Run self-check**. Point out:
   - five mandatory documents still missing (affidavit, TER receipt, occupancy certificate, faculty
     roster, university affiliation);
   - *"Uploaded as Approved Building Plan but content looks like Occupancy Certificate"* — the
     classifier disagrees with the declared type, with its signals;
   - NAAC accreditation expired March 2025.
3. Message: *institutions fix gaps before AICTE ever sees the file.*

## 1:30 – 3:15 · Officer reviews a deficient renewal (`officer.wro`)

1. Log in as `officer.wro` → **Dashboard**: region totals, risk bands, alerts. Open the **PIAT EoA**
   application (high in the queue).
2. **Overview**: compliance score, risk band, checklist with clauses, institutional records
   (approved intake, 49 faculty on record, TER history).
3. **Findings** — open three:
   - **Fire NOC expired** (R-EXP-001, CRITICAL): evidence shows page 1, *"Valid upto
     10/10/2026"*, 16 days before the scrutiny date; the source also reports it.
   - **Faculty count**: declared 52 vs roster 47 vs AICTE records 49 (R-REC-003, R-DOC-001).
   - **Faculty-student ratio** 1200 / 47 = 25.5 > 20 (R-THR-001, illustrative norm).
4. **Verification**: TER receipt *Verification pending* (payment not yet settled at the gateway),
   other documents with source, method and timestamp; the affidavit *Manual review required*
   (no online source).
5. **Infrastructure**: computer-lab photo — 38 terminals detected vs 40 declared; library photo
   has no EXIF. Say: *advisory, tells you where an inspection is worth it.*
6. **Acknowledge** the Fire NOC finding; **Dismiss** the library EXIF finding with a reason.
   Then **Request rectification** selecting the Fire NOC and faculty findings.
7. **Record recommendation** → *Issue deficiency letter*, with a note.

## 3:15 – 4:45 · Forgery indicators (`officer.nro`)

1. Log in as `officer.nro` (Apex is in the Northern region — `officer.wro` cannot see it; mention
   this as RBAC in action). Open the **Apex intake increase**: risk **HIGH**.
2. **Documents** → land deed PDF: producer is an image editor, incremental update, **font
   inconsistency** on the survey number; scanned khatauni extract → **ELA heatmap** with the boxed
   region around the pasted area value.
3. **Verification** → land document **Mismatch detected**: source says survey 118/2 and 5.20 acres;
   document says 148/2 and 12.50 acres — side-by-side comparison.
4. NBA certificate: **QR signature valid but for a different, expired programme** → mismatch.
   Building plan: **QR signature fails** → mismatch. Audited statement: UDIN not found at the
   registry.
5. **Findings** → duplicates: **3 faculty PANs** also on PIAT's roster; **classroom photo identical**
   (same SHA-256) to NVIE's, and geo-tagged ~900 km from the campus.
6. Try **Record recommendation → approve**: blocked, because CRITICAL findings are still open.
   Say: *every flag is a preliminary indicator; the officer verifies.*

## 4:45 – 5:30 · Sources that do not answer (`officer.wro`)

1. Back as `officer.wro`, open the **NVIE new course** application.
2. **Verification**: State NOC *Source unavailable*, university consent *Verification pending*,
   corpus FDR and floor plan *Manual review required*. The application is **MEDIUM risk**;
   its faculty-ratio compliance gap can keep the workflow at **Deficiencies flagged**.
   A source outage alone neither passes nor fails authenticity.
3. Click re-verify on a document to show the timestamped retry.
4. (Optional, 10 s) Open **NVIE EoA**: the clean baseline — everything verified, low risk.

## 5:30 – 6:15 · Decision by the competent authority (`rd.wro`)

1. Log in as `rd.wro`, open **PIAT EoA** (status *Recommended*).
2. Read the officer's recommendation, then **Record decision** → *Issue deficiency letter* with a
   note. Show that the note is mandatory and that the decision is final only for this role.

## 6:15 – 7:00 · Configurable and accountable (`admin`)

1. Log in as `admin` → **Rules & checklists**: open **R-THR-001 Faculty-student ratio**, change the
   maximum (e.g. 20 → 25), save. The ruleset version increments.
2. Back on an application (as an officer), re-run validation — the report shows the new ruleset
   version; the ratio finding changes accordingly.
3. **Verification sources**: switch *Municipal Building & Fire NOC Portal* off — the next check on
   a Fire NOC returns *Source unavailable*. Switch it back on.
4. **Audit log** → **Verify chain**: *valid*, with the number of events checked. Close with:
   *every rule applied, record checked, source response and human action is in a tamper-evident
   chain; the decision stayed with the Regional Director.*

---

### If something goes wrong

- Blank portal or 401: log in again (tokens expire after 8 hours).
- Different findings than listed: re-seed with `--reset`. Expiry checks use today's date unless
  `VERISENSE_REFERENCE_DATE` is set; the scenarios are written for `2026-10-26`
  (`samples/scenarios.json` → `referenceDate`), so for an exact reproduction start the backend
  with `VERISENSE_REFERENCE_DATE=2026-10-26`.
- Backend not reachable from the frontend: confirm it runs on port 8001 (Vite proxies `/api`).
