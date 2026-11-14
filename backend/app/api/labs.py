from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select

from app.core.security import CurrentUser, DbSession
from app.models import Biomarker, LabResult
from app.schemas import BiomarkerOut, LabCreate, LabResultOut, LabUploadResult, TrendOut
from app.services import audit
from app.services.ingestion import parse_csv, parse_fhir, parse_pdf
from app.services.labs import build_trends, create_result, results_for_user, serialize_lab
from app.services.units import UnitError, supported_units

router = APIRouter(prefix="/labs", tags=["labs"])


def _serialize_all(db, user_id: str, *, latest_only: bool = False, category: str | None = None) -> list[LabResultOut]:
    return [
        serialize_lab(result, biomarker)
        for result, biomarker in results_for_user(db, user_id, latest_only=latest_only, category=category)
    ]


@router.get("", response_model=list[LabResultOut])
def list_labs(
    user: CurrentUser,
    db: DbSession,
    latest_only: bool = Query(default=False),
    category: str | None = Query(default=None),
) -> list[LabResultOut]:
    return _serialize_all(db, user.id, latest_only=latest_only, category=category)


@router.get("/biomarkers", response_model=list[BiomarkerOut])
def list_biomarkers(db: DbSession) -> list[BiomarkerOut]:
    rows = db.scalars(select(Biomarker).order_by(Biomarker.sort_order)).all()
    return [BiomarkerOut.model_validate(row) for row in rows]


@router.get("/trends", response_model=list[TrendOut])
def list_trends(user: CurrentUser, db: DbSession) -> list[TrendOut]:
    return build_trends(db, user.id)


@router.post("/manual", response_model=LabResultOut, status_code=status.HTTP_201_CREATED)
def add_manual(payload: LabCreate, user: CurrentUser, db: DbSession) -> LabResultOut:
    try:
        result = create_result(
            db,
            user_id=user.id,
            payload=payload,
            source=payload.source,
            quality_status="self_reported",
            confidence=0.7,
            provenance={"entered_via": "manual_entry"},
        )
    except UnitError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    biomarker = db.get(Biomarker, result.biomarker_id)
    audit.record(
        db,
        user_id=user.id,
        action="labs.create_manual",
        resource_type="lab_result",
        resource_id=result.id,
        detail={"code": biomarker.code if biomarker else None},
    )
    db.commit()
    db.refresh(result)
    return serialize_lab(result, biomarker)


@router.post("/upload", response_model=LabUploadResult)
async def upload_labs(
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
) -> LabUploadResult:
    filename = (file.filename or "upload").strip()
    content = await file.read()
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix == "csv":
        accepted, errors, warnings = parse_csv(db, content, filename)
        confidence = 0.7
    elif suffix in {"json", "fhir"}:
        accepted, errors, warnings = parse_fhir(db, content, filename)
        confidence = 0.65
    elif suffix == "pdf":
        accepted, errors, warnings = parse_pdf(db, content, filename)
        confidence = 0.5
    else:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Supported laboratory uploads: CSV, FHIR JSON, and text-based PDF. Use manual entry for other formats.",
        )

    if not accepted:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "No valid laboratory results were imported.", "errors": errors[:20], "warnings": warnings[:20]},
        )

    created = []
    for payload in accepted[:2000]:
        result = create_result(
            db,
            user_id=user.id,
            payload=payload,
            source=payload.source,
            quality_status="needs_review" if suffix == "pdf" else "unverified_import",
            confidence=confidence,
            provenance={"upload_filename": filename, "parser": suffix, "requires_review": suffix == "pdf"},
        )
        created.append(result)
    audit.record(
        db,
        user_id=user.id,
        action="labs.upload",
        resource_type="lab_import",
        detail={"filename": filename, "parser": suffix, "imported": len(created), "skipped": len(errors)},
    )
    db.commit()
    serialized = []
    for result in created:
        db.refresh(result)
        biomarker = db.get(Biomarker, result.biomarker_id)
        serialized.append(serialize_lab(result, biomarker))
    if len(accepted) > 2000:
        warnings.append("Import limited to 2,000 results per file.")
    return LabUploadResult(
        imported=len(serialized),
        skipped=len(errors),
        warnings=warnings[-20:],
        errors=errors[:20],
        results=serialized,
    )


@router.get("/units/{code}", response_model=dict)
def get_units(code: str, db: DbSession) -> dict:
    biomarker = db.scalar(select(Biomarker).where(Biomarker.code == code))
    if not biomarker:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Unknown biomarker.")
    return {
        "code": biomarker.code,
        "canonical_unit": biomarker.canonical_unit,
        "supported_units": supported_units(biomarker.code, biomarker.canonical_unit),
        "reference_note": biomarker.reference_note,
    }


@router.delete("/{result_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lab(result_id: str, user: CurrentUser, db: DbSession) -> None:
    result = db.scalar(select(LabResult).where(LabResult.id == result_id, LabResult.user_id == user.id))
    if not result:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Laboratory result not found.")
    db.delete(result)
    audit.record(db, user_id=user.id, action="labs.delete", resource_type="lab_result", resource_id=result_id)
    db.commit()
