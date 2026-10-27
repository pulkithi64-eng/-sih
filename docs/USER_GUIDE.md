# User Guide

VeriSense has four roles. Sign in at `http://localhost:5176/portal/login`; demo accounts all use
the password `Demo@2026`.

| Username | Role | Scope |
|---|---|---|
| `inst.piat` | Institution | Own applications (PIAT) |
| `inst.apex` | Institution | Own applications (Apex) |
| `officer.wro` | Scrutiny officer | Western region |
| `officer.nro` | Scrutiny officer | Northern region |
| `rd.wro` | Regional director | Western region, final decisions |
| `admin` | Administrator | Rules, checklists, sources, full audit |

Everything VeriSense produces is marked **Advisory — requires officer review**. Findings point to
evidence; people decide.

---

## 1. Institution (nodal officer)

Navigation: **My applications**, **New application**, **Alerts**.

### Create an application

1. Open **New application**.
2. Choose the **application category** (Extension of Approval, new institution, increase in intake,
   new course, change of name, change of site, closure) and academic year.
3. Fill in **Application details**: programmes and intake, faculty and students, land and building
   (area and location type), fee and accreditation (TER transaction ID, NBA/NAAC claims).
4. The **Required documents** for your category are listed with the regulatory clause each relates
   to. Conditional items appear when your declared values call for them (for example the NBA
   certificate when you claim NBA accreditation).

### Upload documents

- Upload each file against its required-document slot, or under **Other documents**.
- Each upload is processed within seconds. **Live processing results** show the detected document
  type and confidence, the fields read from it (reference number, dates, areas, amounts), and the
  verification state with the issuing authority.
- If the system thinks a file is a different document from the one you selected, you will see a
  finding saying so — check that you uploaded the right file.
- Images and scans are read with OCR; clear, upright, well-lit scans give the best results.

### Check before you submit

**Run self-check** validates the draft against the same rules AICTE will use, without submitting.
Fix missing, expired or inconsistent items while you still can.

### Submit

**Submit to AICTE** runs full validation, assigns a scrutiny officer in your region and moves the
application into review. You can no longer edit it unless AICTE requests rectification.

### Respond to findings

When an officer requests rectification you receive an alert and the application shows **AICTE has
requested rectification**. Under **Respond to findings**:

1. Upload corrected or renewed documents.
2. For each listed finding choose **Mark rectified** (or **Acknowledge**) and write a short note
   explaining what you changed. A note is required.
3. The officer re-runs validation and closes or escalates each finding.

You can see your own applications, documents, findings and report only — never another
institution's.

---

## 2. Scrutiny officer

Navigation: **Dashboard**, **Applications**, **Alerts**, **Rules & checklists** (read),
**Verification sources** (read), **Audit log**.

### Prioritise

The **Dashboard** shows your region's totals (pending validation, deficiencies, source verification
pending, inspection, recommended), breakdowns by status, verification state, category and
severity, recent applications, average validation time and estimated manual effort saved.
**Applications** lists the queue with compliance score, risk band and open critical findings;
filter by status, category, risk band or search. **Alerts** lists critical issues (expired
documents, suspected anomalies, duplicates), missing documents and source failures.

### Review an application

| Tab | What you see |
|---|---|
| **Overview** | Status, scores, checklist with live status and clauses, institutional records already held by AICTE |
| **Documents** | Each file in a viewer beside its classification (with signals), extracted fields (with source text and page), forensic flags and the ELA heatmap |
| **Findings** | Every finding with severity, reason, rule ID, clause and evidence |
| **Verification** | Per document: state, source, method, timestamp, response summary and field-by-field comparison |
| **Infrastructure** | Detections and counts on infrastructure photos, image quality, EXIF date and location |
| **Report** | The structured validation report: summary, checklist, findings, verifications, every rule applied with PASS/FAIL/SKIPPED, ruleset version; PDF download |
| **Audit trail** | Every event for this application in order, with actor and role |

### Work the findings

For each finding open the cited evidence (document page, record value, source response, image
region), then:

- **Acknowledge** — you agree it needs attention.
- **Dismiss** — not a real issue; a reason is required and is kept in the audit trail.
- **Escalate** — needs further action (for example inspection).

Re-run issuing-authority verification on a document when a source was unavailable or pending.
Re-run validation at any time to apply the current ruleset.

Treat forensic and infrastructure findings as pointers: they tell you where to look, not what to
conclude.

### Request rectification and add observations

**Request rectification** lets you select the findings the institution must address and write
instructions; the institution is alerted. **Add observation** records any other remark in the
audit trail.

### Recommend

**Record recommendation** sends your recommended outcome (approve for EoA, issue deficiency letter,
order inspection, reject) to the Regional Director with a note. You cannot make the final
decision, and you cannot recommend approval while a critical finding is still open without a
disposition.

---

## 3. Regional director

Same views as the scrutiny officer, plus **Record decision**:

- Actions: **Approve for EoA**, **Issue deficiency letter**, **Order inspection**, **Reject**.
- A written note is mandatory.
- Approval is blocked while any critical finding is still open without an officer disposition; the
  blocked attempt is recorded.
- The decision, your note, the scores at that moment and the previous status are written to the
  audit chain.

---

## 4. Administrator

Navigation: **Rules & checklists**, **Verification sources**, **Audit log** (plus read access to
applications).

### Rules & checklists

- Enable or disable a rule, change its parameters (thresholds, grace days, tolerances) and severity.
- Edit the required documents for each category (mandatory flag, condition, clause).
- Every change creates a new ruleset version and an audit event with before/after values. Reports
  record the version they were produced with.

See [RULES_AND_CHECKLISTS.md](RULES_AND_CHECKLISTS.md) for the rule types and parameters.

### Verification sources

Each issuing-authority source is listed with its method, document types, online flag, last latency
and success rate. Switching a source off makes subsequent checks return **Source unavailable** —
useful for maintenance windows and for demonstrating that outages are never treated as a pass.

### Audit log

Browse and filter events by action, entity or application. **Verify chain** recomputes the hash
chain and reports whether any event has been altered, and where.

Administrators configure the system; they do not review findings or record decisions.

---

## 5. Statuses at a glance

| Application status | Meaning |
|---|---|
| Draft | Being prepared by the institution |
| Submitted / Under validation | Validation running |
| Deficiencies flagged | Open critical or major findings |
| Source verification pending | Waiting on one or more issuing authorities |
| Under review | No blocking findings; with the officer |
| Rectification requested | Institution asked to correct items |
| Recommended | Officer has recorded a recommendation |
| Inspection ordered | Regional Director ordered a physical inspection |
| Decided | Final decision recorded |

Verification states are explained in [HOW_IT_WORKS.md § 4](HOW_IT_WORKS.md#4-verification-states).
