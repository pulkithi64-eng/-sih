# Rules and Checklists

Every check VeriSense performs at application level is a **rule** in configuration, and every
category's required documents are a **checklist** in configuration. Neither requires a code change
to adjust, so the system can follow revisions of the AICTE Approval Process Handbook (APH).

> **Illustrative values.** Norms (ratios, areas, counts) and clause references in the shipped
> configuration are modelled on the *structure* of APH 2024-27 but are illustrative. They do not
> reproduce official text or numbering; AICTE would set the authoritative values.

Files (in `backend/config/`):

| File | Contents |
|---|---|
| `rules.yaml` | Rule definitions and severity weights |
| `checklists.yaml` | Category → required documents |
| `doc_types.yaml` | Document-type catalogue: label, issuer, validity months, verifiable flag, infrastructure evidence type |
| `authority_keys/` | Public keys of (simulated) issuers used for signed-QR verification |

---

## 1. Versioning and admin edits

- The YAML files are the versioned **baseline** (`version: "2026.1"`).
- Administrators change rules and checklists through the API (and the admin console). Changes are
  stored as overrides in the `config_overrides` table, never by rewriting YAML at runtime.
- Each edit increments a revision counter. The **ruleset version** is `<yaml version>-r<revision>`,
  e.g. `2026.1-r3`; `GET /api/rules/version` returns it.
- Each rule also has its own `version`, incremented on every edit.
- Every validation report and audit event for a validation run records the ruleset version, so it
  is always possible to tell which rules produced a finding.
- Edits are audited (`RULE_UPDATED`, `CHECKLIST_UPDATED`) with before/after values.

| Endpoint | Role | Purpose |
|---|---|---|
| `GET /api/rules` | officer and above | List rules with current overrides applied |
| `PUT /api/rules/{id}` `{enabled?, params?, severity?}` | ADMIN | Change a rule |
| `GET /api/checklists` | any | All category checklists |
| `PUT /api/checklists/{category}` `[items]` | ADMIN | Replace a category checklist |

## 2. Checklists

```yaml
# backend/config/checklists.yaml
version: "2026.1"
categories:
  EOA:
    label: Extension of Approval (EoA)
    items:
      - {docType: FIRE_NOC, mandatory: true,
         clause: "APH 2024-27 (illustrative) — Ch. III, Safety: valid Fire NOC"}
      - {docType: NBA_ACCREDITATION, mandatory: false,
         when: {field: formData.nbaAccredited, truthy: true},
         clause: "APH 2024-27 (illustrative) — Accreditation status (if claimed)"}
```

| Key | Meaning |
|---|---|
| `docType` | One of the IDs in `doc_types.yaml` |
| `mandatory` | Required for every application in the category |
| `when` | Optional condition that makes the item required. Field may be `formData.<name>`, `records.<path>` or `category`; operators `equals`, `in`, `gt`, `gte`, `lt`, `exists`, `truthy` |
| `clause` | Regulatory pointer shown with the item and with any finding |

Categories: `EOA`, `NEW_INSTITUTION`, `INTAKE_INCREASE`, `NEW_COURSE`, `CHANGE_OF_NAME`,
`CHANGE_OF_SITE`, `CLOSURE`.

At validation time each item gets a status:

| Status | Rule |
|---|---|
| `PRESENT` | A document of that type is uploaded and current |
| `MISSING` | Required and not uploaded |
| `EXPIRED` | Uploaded but past its expiry date, or the source reported it expired |
| `INVALID` | Uploaded but source verification returned a mismatch |
| `NOT_REQUIRED` | Optional or condition not met, and not uploaded |

## 3. Rule anatomy

```yaml
- id: R-EXP-001                 # stable identifier, cited on every finding
  name: Fire NOC valid
  description: Fire safety NOC must be valid on the date of scrutiny.
  categories: [ALL]             # or a list of categories
  type: DOCUMENT_EXPIRY         # one of the 13 rule types below
  kind: EXPIRED_DOCUMENT        # Finding kind produced on failure
  params: {docTypes: [FIRE_NOC], graceDays: 0, warnDays: 60}
  severity: CRITICAL            # CRITICAL | MAJOR | MINOR | INFO
  clause: "APH 2024-27 (illustrative) — Ch. III, Safety norms: valid Fire NOC"
  enabled: true
  version: 1
```

`severityWeights: {CRITICAL: 5, MAJOR: 3, MINOR: 1, INFO: 0}` at the top of the file controls how
much each rule counts in the compliance score (see [HOW_IT_WORKS.md](HOW_IT_WORKS.md#scoring)).

Each evaluated rule reports `PASS`, `FAIL` or `SKIPPED` (disabled, not applicable to the category,
nothing to check, or an evaluation error — a broken rule never aborts validation), with the number
of checks, failures and a one-line detail.

## 4. Rule types and parameters

| Type | Parameters | What it does |
|---|---|---|
| `REQUIRED_DOCUMENT` | – | Every mandatory or triggered conditional checklist item is present |
| `DOCUMENT_EXPIRY` | `docTypes` (or `[ALL]`), `excludeDocTypes`, `graceDays`, `warnDays`, `maxAgeDays`, `checkRecords` | Expiry vs scrutiny date; MINOR warning when expiring within `warnDays`; documents older than `maxAgeDays` (e.g. affidavits); with `checkRecords`, accreditation and affidavit records too |
| `FIELD_PRESENT` | `fields` (form), `documentFields` {docType: [field]} | Declared fields present; key fields readable on documents |
| `FIELD_MATCH_RECORD` | `formField`, `recordPath`, `tolerance`, `comparison`, `expectedIn`, `expectedMax`, `perProgramme`, `allowIncreaseCategories`, `requirePreviousYear` | Declared value vs AICTE records |
| `FIELD_MATCH_DOCUMENT` | `formField` (or `@institution.name`), `docType` (one or list), `extractedField`, `tolerance`, `minSimilarity` | Declared value vs value extracted from a document |
| `THRESHOLD` | `metric` (`faculty_student_ratio`, `land_area_acres`, `builtup_area_per_intake`), `max` / `min` / `minByLocation` / `defaultMin`, `programmeDurationYears` | Norm checks |
| `CADRE_RATIO` | `ratio` (e.g. `[1, 2, 6]`), `tolerance` | Professor : Associate : Assistant mix |
| `TER_PAYMENT` | `formField`, `docType`, `extractedField` | TER paid for the year in records and receipt matches the declared transaction |
| `DUPLICATE_DOCUMENT` | `maxHamming`, `ignoreDocTypes` | Same SHA-256, or perceptual hash within `maxHamming` bits, at another institution |
| `DUPLICATE_FACULTY` | – | Same PAN in another institution's records or roster |
| `FORENSIC_FLAG` | `minSeverity` | Turns forensic indicators into findings |
| `SOURCE_VERIFICATION` | `mismatchSeverity`, `manualReviewSeverity` | Turns verification outcomes into findings |
| `INFRA_EVIDENCE` | `evidenceType`, `docType`, `label` (list), `minCount`, `maxAgeDays`, `maxDistanceKm`, `minBlurScore` | Object counts, recency, geo-distance and sharpness of infrastructure photos |

### Record paths

`recordPath` addresses the institution's records (`GET /api/institutions/{id}/records`) with a small
expression language:

| Expression | Example | Result |
|---|---|---|
| dotted path | `landAndBuilding.landAreaAcres` | value |
| `count(list)` | `count(faculty)` | number of items |
| `count(list[k=v])` | `count(deficiencyHistory[status=OPEN])` | filtered count |
| `sum(list.field)` | `sum(approvedProgrammes.intake)` | sum |
| `latest(list).field` | `latest(previousApprovals).status` | field of the most recent item (by year/date) |

## 5. Shipped rules (29)

| ID | Name | Type | Severity |
|---|---|---|---|
| R-CHK-001 | Mandatory documents present | REQUIRED_DOCUMENT | CRITICAL |
| R-FLD-001 | Core declared fields present | FIELD_PRESENT | MAJOR |
| R-FLD-002 | Key reference fields readable on verifiable documents | FIELD_PRESENT | MINOR |
| R-EXP-001 | Fire NOC valid | DOCUMENT_EXPIRY | CRITICAL |
| R-EXP-002 | Accreditation valid (NBA / NAAC) | DOCUMENT_EXPIRY | MAJOR |
| R-EXP-003 | Affidavit for the current year | DOCUMENT_EXPIRY | MAJOR |
| R-EXP-004 | Other dated documents within validity | DOCUMENT_EXPIRY | MAJOR |
| R-REC-001 | Previous Extension of Approval on record | FIELD_MATCH_RECORD | CRITICAL |
| R-REC-002 | Declared intake within approved intake | FIELD_MATCH_RECORD | CRITICAL |
| R-REC-003 | Declared faculty count matches AICTE faculty records | FIELD_MATCH_RECORD | MAJOR |
| R-REC-004 | Declared land area matches records | FIELD_MATCH_RECORD | MAJOR |
| R-REC-005 | Declared built-up area matches records | FIELD_MATCH_RECORD | MAJOR |
| R-REC-006 | No open deficiencies from previous cycles | FIELD_MATCH_RECORD | MAJOR |
| R-DOC-001 | Faculty count consistent with roster | FIELD_MATCH_DOCUMENT | MAJOR |
| R-DOC-002 | Land area consistent with land document | FIELD_MATCH_DOCUMENT | MAJOR |
| R-DOC-003 | Built-up area consistent with occupancy certificate / floor plan | FIELD_MATCH_DOCUMENT | MAJOR |
| R-DOC-004 | Institution name consistent across documents | FIELD_MATCH_DOCUMENT | MAJOR |
| R-THR-001 | Faculty-student ratio (illustrative max 20) | THRESHOLD | CRITICAL |
| R-THR-002 | Minimum land area by location | THRESHOLD | MAJOR |
| R-THR-003 | Built-up area per sanctioned intake | THRESHOLD | MAJOR |
| R-CAD-001 | Faculty cadre ratio (illustrative 1:2:6) | CADRE_RATIO | MAJOR |
| R-TER-001 | TER paid for the current academic year | TER_PAYMENT | CRITICAL |
| R-DUP-001 | Document reused across institutions | DUPLICATE_DOCUMENT | CRITICAL |
| R-DUP-002 | Faculty shown at more than one institution | DUPLICATE_FACULTY | CRITICAL |
| R-FOR-001 | Document forensic anomalies | FORENSIC_FLAG | MAJOR |
| R-SRC-001 | Verification with issuing authority | SOURCE_VERIFICATION | CRITICAL |
| R-INF-001 | Computer lab evidence | INFRA_EVIDENCE | MAJOR |
| R-INF-002 | Classroom evidence | INFRA_EVIDENCE | MINOR |
| R-INF-003 | Infrastructure photo authenticity | INFRA_EVIDENCE | MINOR |

In addition to the configured rules, a few per-document checks always run: declared vs detected
document type (classification), pipeline errors (unreadable files) and infrastructure image flags.

## 6. Worked example: tightening the faculty-student ratio

Suppose a revised handbook lowers the illustrative ratio from 1:20 to 1:15.

```http
PUT /api/rules/R-THR-001
Authorization: Bearer <admin token>
Content-Type: application/json

{"params": {"metric": "faculty_student_ratio", "max": 15, "programmeDurationYears": 4}}
```

Result:

1. `R-THR-001` becomes version 2; the ruleset version moves from `2026.1-r0` to `2026.1-r1`.
2. An audit event `RULE_UPDATED` records `params.max: 20 → 15` and the new versions.
3. The next validation of any application (on submit, or when an officer clicks re-run) uses the
   new limit; its report shows `rulesetVersion: 2026.1-r1`.
4. Re-validation is idempotent: untouched `OPEN` findings are regenerated from the current rules
   (so a finding that no longer fires disappears), while findings an officer or institution has
   acted on (acknowledged, dismissed, escalated, rectified, or annotated) are kept. The audit event
   of each run records how many findings were created, removed and kept.

To switch a rule off temporarily: `PUT /api/rules/R-INF-002 {"enabled": false}` — it then appears in
reports as `SKIPPED: rule disabled by administrator`.

## 7. Adding a document to a checklist

```http
PUT /api/checklists/EOA
[
  {"docType": "PREVIOUS_EOA_LETTER", "mandatory": true, "clause": "..."},
  ...,
  {"docType": "STRUCTURAL_STABILITY_CERT", "mandatory": true,
   "clause": "APH 2024-27 (illustrative) — Ch. III, Structural stability"}
]
```

Unknown `docType` values are rejected with `422`. The change is audited and bumps the ruleset
version.

## 8. Adding a new rule type

New *instances* of existing types need only YAML. A genuinely new kind of check needs a small
evaluator function in `backend/app/engine/validator.py` (`r_<type>(rule, ctx) -> Outcome`)
registered in `EVALUATORS`, and the type name added to `RULE_TYPES` in `rules_loader.py`. The
evaluator receives the application context (form data, documents with extracted fields,
institutional records, verification and forensic results) and returns checks, failures and
findings with evidence.
