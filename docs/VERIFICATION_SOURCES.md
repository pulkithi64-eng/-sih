# Verification with Issuing Authorities

PS 26261 asks for documents to be verified with the authority that issued them — through APIs,
portals, DigiLocker, QR codes, digital signatures or reference numbers — and for every check to
record the source, timestamp and result using six states, routing inconclusive cases to manual
review.

> **Prototype status.** All issuing authorities in this repository are **simulated** services
> (`backend/app/mock_authorities`, mounted at `/mock/*`) with their own records and Ed25519 signing
> keys. The adapter layer that calls them is the same layer a production deployment would use with
> authorised real APIs. No real government system is contacted.

---

## 1. Two independent ways to verify

### 1.1 Signed QR payloads (offline-verifiable)

Simulated issuers print a QR code on their certificates. The payload is:

```text
base64url( JSON { "iss": <issuer>, "kid": <key id>, "claims": {...}, "sig": <base64url Ed25519 signature> } )
```

- The signature covers the canonical JSON of `{iss, kid, claims}` (sorted keys, compact separators),
  so neither the claims nor the issuer/key binding can be altered without invalidating it.
- Public keys live in `backend/config/authority_keys/<kid>.pub` (PEM). Private keys exist only under
  `samples/tools/keys/` and are used by the synthetic data generator.
- `pipeline/qr.py` renders each page and decodes QR codes with OpenCV; `pipeline/signature.py`
  verifies the signature.
- The claims (reference number, holder, dates, area, intake, ...) are then compared field by field
  with the values extracted from the printed text. A valid signature over claims that differ from
  the printed page is reported as a **mismatch** — the typical signature of a certificate whose text
  was edited after issue.

This mirrors how real Indian documents increasingly carry signed QR codes (for example e-stamp
papers, DigiLocker-issued documents and many municipal certificates).

### 1.2 Source lookup by reference number

Where a document type has a registered source, the adapter queries it by the extracted reference
number and compares authority-held fields with the submitted ones.

## 2. Adapter model

`backend/app/adapters/base.py` defines `Adapter`:

| Attribute | Meaning |
|---|---|
| `id`, `name`, `issuer` | Identity of the source shown to officers |
| `doc_types` | Document types this source can verify |
| `method` | `API`, `DIGILOCKER` or `PORTAL` (QR checks report `QR_SIGNATURE`; manual routing reports `MANUAL`) |
| `paths` | Lookup path per document type, e.g. `/fire/noc/{ref}` |
| `compare` | Fields compared with the source, per document type |
| `ref_field` | Extracted field used as the lookup key (default `referenceNo`, `udin` for CA certificates) |

`backend/app/adapters/registry.py` holds the adapters and produces the verdict:

| Source id | Simulated authority | Method | Document types | Fields compared |
|---|---|---|---|---|
| `digilocker` | DigiLocker issued documents (universities, state DTE, registrars) | DIGILOCKER | `UNIVERSITY_AFFILIATION`, `STATE_GOVT_NOC`, `SOCIETY_TRUST_REGISTRATION` | institution name, university, academic year, intake, course, trust name |
| `nba` | NBA accreditation registry | API | `NBA_ACCREDITATION` | institution, programme, validity |
| `naac` | NAAC accreditation registry | API | `NAAC_ACCREDITATION` | institution, grade, CGPA, validity |
| `municipal_fire` | Municipal building and Fire NOC portal | PORTAL | `FIRE_NOC`, `OCCUPANCY_CERTIFICATE`, `BUILDING_PLAN_APPROVAL` | institution, built-up area, issue and expiry dates |
| `land_records` | State land records | PORTAL | `LAND_DOCUMENT` | survey number, area, owner, village, district |
| `ter_payments` | AICTE TER payment gateway | API | `TER_PAYMENT_RECEIPT` | amount, application number, date |
| `aicte_eoa` | AICTE approval records | API | `PREVIOUS_EOA_LETTER` | institution, permanent ID, academic year, intake |
| `ca_udin` | ICAI UDIN registry | API | `AUDITED_FINANCIAL_STATEMENT` | financial year, membership number, institution |

Live list with latency and success rate: `GET /api/sources` (officer and above).

### Transport

Adapters call `VERISENSE_MOCK_BASE` (default `http://localhost:8001/mock`) over HTTP with a 5 s read
timeout (`VERISENSE_MOCK_TIMEOUT`) and 1.5 s connect timeout. `VERISENSE_MOCK_MODE` selects
`auto` (HTTP, falling back to an in-process call if the server is not reachable), `http` (HTTP only;
connection failure becomes `SOURCE_UNAVAILABLE`) or `inprocess` (tests and seeding).

### Source state

Administrators can switch a source off (`POST /api/sources/{id}/toggle`). The flag and per-source
call statistics are persisted in `backend/data/sources_state.json` and shared with the simulated
services, so an "offline" source behaves like a real outage.

## 3. Decision logic (six states)

Implemented in `Registry.verify()`; every outcome is advisory.

1. **Not an issued document.** Faculty rosters and infrastructure photographs are institution
   evidence → `NOT_APPLICABLE` (they are checked by record cross-checks and image analysis instead).
2. **Signed QR present** (checked first, works offline):
   - signature invalid or key unknown → `MISMATCH_DETECTED`
   - signature valid but claims differ from printed text → `MISMATCH_DETECTED`
   - signature valid, claims expired → `EXPIRED`
   - signature valid and matching → `VERIFIED` (method `QR_SIGNATURE`), unless the online source
     additionally gives a definitive negative (revoked, expired, mismatch).
3. **No usable QR** — query the source by reference number:

| Situation | State |
|---|---|
| No source registered for the document type | `MANUAL_REVIEW_REQUIRED` |
| Reference number could not be extracted | `MANUAL_REVIEW_REQUIRED` |
| Source switched off, HTTP 5xx, connection refused | `SOURCE_UNAVAILABLE` |
| HTTP 202 (queued) or read timeout | `VERIFICATION_PENDING` |
| HTTP 404 and reference read with confidence ≥ 0.8 | `MISMATCH_DETECTED` (authority has no such record) |
| HTTP 404 and lower-confidence reference | `MANUAL_REVIEW_REQUIRED` (likely an OCR error) |
| Record `REVOKED` | `MISMATCH_DETECTED` |
| Record `EXPIRED`, or validity date in the past | `EXPIRED` |
| Any compared field differs | `MISMATCH_DETECTED` |
| Otherwise | `VERIFIED` |

Each result stores `status, source, sourceName, method, checkedAt, responseSummary,
comparisons[{field, submitted, source, match}], reason, latencyMs, transport`. Officers can re-run a
check at any time (`POST /api/documents/{id}/verify`); each run is written to the audit chain.

The rule `R-SRC-001` turns non-verified outcomes into findings of kind `VERIFICATION`, and the
validator raises alerts for unavailable or pending sources.

## 4. Plugging in a real source

A real integration is a new `Adapter` entry (or a subclass overriding `lookup`) — the rule engine,
findings, report and UI do not change.

1. **Obtain authorisation.** Each authority must authorise AICTE's use of its API: MoU or
   onboarding, credentials, permitted purposes, rate limits and data-retention terms.
2. **Implement transport.** Override `Adapter.lookup(doc_type, ref)` to call the real endpoint with
   the required authentication (OAuth client credentials, API key, mutual TLS) and map the response
   to a `SourceResponse(status_code, body, latency_ms, transport)`.
3. **Map fields.** Set `compare` to the fields the authority returns; normalise names to the
   extracted-field vocabulary (`referenceNo`, `issueDate`, `expiryDate`, `institutionName`, ...).
4. **Register keys.** For QR-signing issuers, add the issuer's public key to
   `config/authority_keys/` and its entry to `issuers.json`.
5. **Test** with recorded responses, including outages and timeouts, and confirm the six-state
   mapping.

### Example: DigiLocker

DigiLocker exposes Issuer and Requester (Authorised Partner) APIs. As an authorised requester,
AICTE could, with the institution's consent, pull the issuer-signed copy of a document by its
DigiLocker URI and compare it with the uploaded scan. The `digilocker` adapter already models this
flow (lookup by URI, compare institution, university, academic year and intake); a production
version would replace the `/mock/digilocker/issued/{uri}` path with the Requester API call and the
consent flow.

### Example: NBA / NAAC

Accreditation bodies publish accredited programmes and institutions. A production adapter would
query their registry by accreditation reference or institution code and compare programme, grade
and validity — exactly the fields compared by the simulated `nba` and `naac` adapters.

### Other likely sources

State land-record portals (record of rights by survey number), urban local body portals (fire NOC,
occupancy, building permission), ICAI UDIN for audited statements, and AICTE's own TER payment and
approval databases.

## 5. Safeguards specific to verification

- A source failure is never treated as a pass; it is `SOURCE_UNAVAILABLE` with a timestamp.
- A missing record is reported as a mismatch only when the reference number was read with high
  confidence; otherwise it is routed to manual review.
- Full source responses are kept with the document and summarised in the audit event.
- Simulated responses are labelled as simulated (`simulated: true` on each source).
