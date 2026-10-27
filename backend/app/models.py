"""ORM models (contract section 3)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    event,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(32))
    region: Mapped[str | None] = mapped_column(String(8), nullable=True)
    institution_id: Mapped[int | None] = mapped_column(ForeignKey("institutions.id"), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Institution(Base):
    __tablename__ = "institutions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    permanent_id: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(256))
    type: Mapped[str] = mapped_column(String(64), default="Private-Self Financing")
    state: Mapped[str] = mapped_column(String(64), default="")
    city: Mapped[str] = mapped_column(String(64), default="")
    region: Mapped[str] = mapped_column(String(8))
    established_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trust_name: Mapped[str] = mapped_column(String(256), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    campus_gps: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # InstitutionalRecords ("already in AICTE systems")
    records: Mapped[dict] = mapped_column(JSON, default=dict)


class Application(Base):
    __tablename__ = "applications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_no: Mapped[str] = mapped_column(String(48), unique=True, index=True)
    key: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"), index=True)
    category: Mapped[str] = mapped_column(String(32))
    academic_year: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(40), default="DRAFT")
    region: Mapped[str] = mapped_column(String(8))
    assigned_officer: Mapped[str | None] = mapped_column(String(64), nullable=True)
    form_data: Mapped[dict] = mapped_column(JSON, default=dict)
    scenario: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_findings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    compliance_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_band: Mapped[str] = mapped_column(String(8), default="LOW")
    checklist: Mapped[list] = mapped_column(JSON, default=list)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    recommendation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    decision: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    institution: Mapped[Institution] = relationship(lazy="joined")
    documents: Mapped[list["Document"]] = relationship(
        back_populates="application", cascade="all, delete-orphan", order_by="Document.id"
    )
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="application", cascade="all, delete-orphan", order_by="Finding.id"
    )


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    doc_type: Mapped[str] = mapped_column(String(48))
    declared_doc_type: Mapped[str | None] = mapped_column(String(48), nullable=True)
    file_name: Mapped[str] = mapped_column(String(256))
    file_path: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(String(96))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    phash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    uploaded_by: Mapped[str] = mapped_column(String(64))
    classification: Mapped[dict] = mapped_column(JSON, default=dict)
    ocr: Mapped[dict] = mapped_column(JSON, default=dict)
    ocr_text: Mapped[str] = mapped_column(Text, default="")
    ocr_blocks: Mapped[list] = mapped_column(JSON, default=list)
    extracted_fields: Mapped[dict] = mapped_column(JSON, default=dict)
    issuer: Mapped[str | None] = mapped_column(String(256), nullable=True)
    reference_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    issue_date: Mapped[str | None] = mapped_column(String(16), nullable=True)
    expiry_date: Mapped[str | None] = mapped_column(String(16), nullable=True)
    verification: Mapped[dict] = mapped_column(JSON, default=dict)
    qr: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    forensics: Mapped[dict] = mapped_column(JSON, default=dict)
    ela_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    infra: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pipeline_errors: Mapped[list] = mapped_column(JSON, default=list)
    processing_ms: Mapped[int] = mapped_column(Integer, default=0)

    application: Mapped[Application] = relationship(back_populates="documents")


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    kind: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(256))
    reason: Mapped[str] = mapped_column(Text)
    rule_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    clause: Mapped[str | None] = mapped_column(String(256), nullable=True)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default="OPEN")
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(256), index=True)
    origin: Mapped[str] = mapped_column(String(16), default="VALIDATOR")  # PIPELINE | VALIDATOR | OFFICER
    human_modified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    application: Mapped[Application] = relationship(back_populates="findings")


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(48))
    severity: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    read: Mapped[bool] = mapped_column(Boolean, default=False)

    application: Mapped[Application] = relationship(lazy="joined")


class ValidationRun(Base):
    __tablename__ = "validation_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    ruleset_version: Mapped[str] = mapped_column(String(32))
    duration_seconds: Mapped[float] = mapped_column(Float)
    triggered_by: Mapped[str] = mapped_column(String(64))
    report: Mapped[dict] = mapped_column(JSON)


class ConfigOverride(Base):
    """Admin edits to rules/checklists (YAML stays the versioned baseline)."""

    __tablename__ = "config_overrides"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))  # RULE | CHECKLIST | META
    key: Mapped[str] = mapped_column(String(64))
    data: Mapped[dict | list] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    updated_by: Mapped[str] = mapped_column(String(64), default="system")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[str] = mapped_column(String(40))  # ISO-8601 UTC string, part of the hashed payload
    actor: Mapped[str] = mapped_column(String(64))
    actor_role: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[str] = mapped_column(String(64), index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True)


# --- audit immutability --------------------------------------------------------------------

class AuditImmutableError(RuntimeError):
    pass


@event.listens_for(AuditEvent, "before_update")
def _no_update(*_a):
    raise AuditImmutableError("audit events are append-only")


@event.listens_for(AuditEvent, "before_delete")
def _no_delete(*_a):
    raise AuditImmutableError("audit events are append-only")


def install_audit_triggers(engine) -> None:
    """Database-level guard (SQLite triggers) so even raw SQL cannot alter the audit log."""
    if not str(engine.url).startswith("sqlite"):
        return
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_events "
            "BEGIN SELECT RAISE(ABORT, 'audit events are append-only'); END"
        ))
        conn.execute(text(
            "CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_events "
            "BEGIN SELECT RAISE(ABORT, 'audit events are append-only'); END"
        ))
