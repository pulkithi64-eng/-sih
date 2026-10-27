"""Institution management router: list, search, statistics, create, update, and records."""
from __future__ import annotations

from collections import Counter
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import audit
from ..db import get_db
from ..models import Application, Institution, User
from ..schemas import (
    InstitutionCreate,
    InstitutionPatch,
    application_out,
    institution_out,
)
from ..security import (
    ADMIN,
    INSTITUTION,
    OFFICER_PLUS,
    RD,
    get_current_user,
    require_roles,
)

router = APIRouter(prefix="/institutions", tags=["institutions"])


def _check(user: User, inst: Institution | None) -> Institution:
    if inst is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Institution not found")
    if user.role == INSTITUTION and user.institution_id != inst.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Institution not found")
    if user.role not in (INSTITUTION, ADMIN) and (not user.region or inst.region != user.region):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Institution not found")
    return inst


def _compute_inst_summary(inst: Institution, apps: list[Application]) -> dict[str, Any]:
    base = institution_out(inst)
    records = inst.records or {}
    programmes = records.get("approvedProgrammes") or []
    faculty = records.get("faculty") or []
    total_intake = sum(p.get("intake", 0) for p in programmes if isinstance(p, dict))

    app_count = len(apps)
    latest_app = apps[0] if apps else None
    open_findings = sum(
        sum(1 for f in a.findings if f.status in ("OPEN", "ACKNOWLEDGED", "ESCALATED"))
        for a in apps
    )
    avg_compliance = (
        round(sum(a.compliance_score for a in apps) / app_count, 1)
        if app_count > 0
        else 0.0
    )

    highest_risk = "LOW"
    for a in apps:
        if a.risk_band == "HIGH":
            highest_risk = "HIGH"
            break
        if a.risk_band == "MEDIUM" and highest_risk != "HIGH":
            highest_risk = "MEDIUM"

    base["stats"] = {
        "applicationsCount": app_count,
        "latestStatus": latest_app.status if latest_app else "NO_APPLICATIONS",
        "latestAcademicYear": latest_app.academic_year if latest_app else None,
        "latestAppId": latest_app.id if latest_app else None,
        "openFindings": open_findings,
        "averageCompliance": avg_compliance,
        "riskBand": highest_risk,
        "programmesCount": len(programmes),
        "totalIntake": total_intake,
        "facultyCount": len(faculty),
        "naacGrade": (records.get("accreditation") or {}).get("naac", {}).get("grade"),
        "landAreaAcres": (records.get("landAndBuilding") or {}).get("landAreaAcres"),
    }
    return base


@router.get("")
def list_institutions(
    region: str | None = None,
    inst_type: str | None = Query(None, alias="type"),
    q: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Institution)
    if user.role == INSTITUTION:
        stmt = stmt.where(Institution.id == (user.institution_id or -1))
    elif user.role != ADMIN:
        stmt = stmt.where(Institution.region == user.region) if user.region else stmt.where(False)

    if region and user.role == ADMIN:
        stmt = stmt.where(Institution.region == region)
    if inst_type:
        stmt = stmt.where(Institution.type == inst_type)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Institution.name.ilike(like),
                Institution.permanent_id.ilike(like),
                Institution.city.ilike(like),
                Institution.state.ilike(like),
            )
        )

    institutions = db.execute(stmt.order_by(Institution.name)).scalars().all()

    # Preload applications for fast dashboard rendering
    out = []
    for inst in institutions:
        apps = (
            db.execute(
                select(Application)
                .where(Application.institution_id == inst.id)
                .order_by(Application.updated_at.desc())
            )
            .scalars()
            .all()
        )
        out.append(_compute_inst_summary(inst, list(apps)))

    return out


@router.get("/overview/stats")
def overview_stats(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*OFFICER_PLUS)),
):
    """Aggregate statistics for the Institution Management Dashboard."""
    stmt = select(Institution)
    if user.role != ADMIN:
        stmt = stmt.where(Institution.region == user.region) if user.region else stmt.where(False)
    institutions = db.execute(stmt).scalars().all()

    app_stmt = select(Application)
    if user.role != ADMIN:
        app_stmt = app_stmt.where(Application.region == user.region) if user.region else app_stmt.where(False)
    applications = db.execute(app_stmt).scalars().all()

    by_region = Counter(i.region for i in institutions)
    by_type = Counter(i.type for i in institutions)

    total_programs = 0
    total_faculty = 0
    total_intake = 0
    for i in institutions:
        recs = i.records or {}
        progs = recs.get("approvedProgrammes") or []
        fac = recs.get("faculty") or []
        total_programs += len(progs)
        total_faculty += len(fac)
        total_intake += sum(p.get("intake", 0) for p in progs if isinstance(p, dict))

    high_risk_institutions = 0
    inst_ids_with_high_risk = {a.institution_id for a in applications if a.risk_band == "HIGH"}
    high_risk_institutions = len(inst_ids_with_high_risk.intersection({i.id for i in institutions}))

    return {
        "totalInstitutions": len(institutions),
        "totalApplications": len(applications),
        "totalApprovedProgrammes": total_programs,
        "totalSanctionedIntake": total_intake,
        "totalRecordedFaculty": total_faculty,
        "highRiskInstitutions": high_risk_institutions,
        "byRegion": dict(by_region),
        "byType": dict(by_type),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_institution(
    body: InstitutionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(ADMIN, RD)),
):
    """Admin or Regional Director creates a new Institution entry."""
    if user.role == RD and (not user.region or body.region.upper() != user.region):
        raise HTTPException(403, "Directors may only create institutions in their assigned region")
    existing = db.execute(
        select(Institution).where(Institution.permanent_id == body.permanent_id.strip())
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(400, f"Institution with Permanent ID {body.permanent_id} already exists")

    inst = Institution(
        permanent_id=body.permanent_id.strip(),
        name=body.name.strip(),
        type=body.type,
        state=body.state,
        city=body.city,
        region=body.region.upper(),
        established_year=body.established_year,
        trust_name=body.trust_name,
        address=body.address,
        campus_gps=body.campus_gps,
        records=body.records or {},
    )
    db.add(inst)
    db.flush()
    audit.record(
        db,
        user,
        "INSTITUTION_CREATED",
        "Institution",
        inst.id,
        {"name": inst.name, "permanentId": inst.permanent_id, "region": inst.region},
    )
    db.commit()
    db.refresh(inst)
    return institution_out(inst)


@router.get("/{inst_id}")
def get_institution(
    inst_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    inst = _check(user, db.get(Institution, inst_id))
    apps = (
        db.execute(
            select(Application)
            .where(Application.institution_id == inst.id)
            .order_by(Application.updated_at.desc())
        )
        .scalars()
        .all()
    )
    return _compute_inst_summary(inst, list(apps))


@router.patch("/{inst_id}")
def update_institution(
    inst_id: int,
    body: InstitutionPatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    inst = _check(user, db.get(Institution, inst_id))
    # Institution users can only update address / gps / trust details, not permanentId/region
    if user.role == INSTITUTION:
        allowed = {"address", "campus_gps", "trust_name"}
        if set(body.model_fields_set) - allowed:
            raise HTTPException(403, "Institutions may only update address, campus GPS and trust details")
    elif user.role != ADMIN:
        raise HTTPException(403, "Only administrators may change institutional records")

    changes: dict[str, Any] = {}
    patch_data = body.model_dump(exclude_unset=True)
    for field_name, value in patch_data.items():
        if value is not None and hasattr(inst, field_name):
            old_val = getattr(inst, field_name)
            if old_val != value:
                setattr(inst, field_name, value)
                changes[field_name] = {"before": old_val, "after": value}

    if changes:
        audit.record(db, user, "INSTITUTION_UPDATED", "Institution", inst.id, {"changes": changes})
        db.commit()
        db.refresh(inst)

    return institution_out(inst)


@router.get("/{inst_id}/records")
def records(
    inst_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _check(user, db.get(Institution, inst_id)).records or {}


@router.get("/{inst_id}/applications")
def institution_applications(
    inst_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    inst = _check(user, db.get(Institution, inst_id))
    apps = (
        db.execute(
            select(Application)
            .where(Application.institution_id == inst.id)
            .order_by(Application.updated_at.desc())
        )
        .scalars()
        .all()
    )
    return [application_out(a) for a in apps]


@router.get("/{inst_id}/stats")
def institution_stats(
    inst_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    inst = _check(user, db.get(Institution, inst_id))
    apps = (
        db.execute(
            select(Application)
            .where(Application.institution_id == inst.id)
            .order_by(Application.updated_at.desc())
        )
        .scalars()
        .all()
    )

    recs = inst.records or {}
    progs = recs.get("approvedProgrammes") or []
    faculty = recs.get("faculty") or []

    statuses = Counter(a.status for a in apps)
    risk_bands = Counter(a.risk_band for a in apps)

    return {
        "institutionId": inst.id,
        "permanentId": inst.permanent_id,
        "name": inst.name,
        "region": inst.region,
        "establishedYear": inst.established_year,
        "totalApplications": len(apps),
        "applicationsByStatus": dict(statuses),
        "riskBands": dict(risk_bands),
        "approvedProgrammes": progs,
        "facultyCount": len(faculty),
        "accreditation": recs.get("accreditation", {}),
        "landAndBuilding": recs.get("landAndBuilding", {}),
    }
