# ADR 0001 - Retain FastAPI, defer additional backend services

Status: accepted for this implementation (27 October 2026); no performance measurements collected in this environment.

FastAPI already owns JWT authorization, SQLAlchemy, application lifecycle, local document AI, adapters, rules, reports and audit. React uses a centralized REST client. No missing integration currently needs a second orchestration runtime.

| Option | Benefit | Cost / decision |
|---|---|---|
| FastAPI only | One authorization boundary and transaction model; preserves document AI | Retain. Add durable jobs/migrations in this service when tested. |
| FastAPI plus Express gateway | Could aggregate independent downstream services or provide a browser-specific API | Extra deployment, auth forwarding and observability boundary without measured benefit here; deferred. |
| Isolated PHP REST client | Could demonstrate curriculum interoperability | No curriculum requirement was supplied; no example added. Never duplicate authentication or SQL ownership. |

Reconsider Express only with measured latency/operational requirements and contract tests. A PHP example, if requested, must use existing REST over an authenticated server-side client, with no embedded credentials. Neither alternative may replace FastAPI document AI. No new service is introduced.
