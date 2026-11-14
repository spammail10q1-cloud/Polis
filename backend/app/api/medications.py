from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.security import CurrentUser, DbSession
from app.models import Medication, MedicationExposure
from app.schemas import (
    ExposureCreate,
    ExposureOut,
    ExposureUpdate,
    InteractionOut,
    MedicationOut,
    SearchMedicationOut,
)
from app.services import audit
from app.services.drugs import (
    active_exposures,
    exposure_out,
    interactions_between,
    resolve_medication,
    search,
)

router = APIRouter(prefix="/medications", tags=["medications"])


@router.get("/catalog", response_model=list[SearchMedicationOut])
def catalog(db: DbSession, query: str | None = Query(default=None, max_length=120)) -> list[SearchMedicationOut]:
    return [
        SearchMedicationOut(
            id=med.id,
            name=med.name,
            generic_name=med.generic_name,
            drug_class=med.drug_class,
            is_simulation_eligible=med.is_simulation_eligible,
        )
        for med in search(db, query)
    ]


@router.get("", response_model=list[ExposureOut])
def list_medications(user: CurrentUser, db: DbSession, active_only: bool = Query(default=False)) -> list[ExposureOut]:
    stmt = (
        select(MedicationExposure, Medication)
        .join(Medication, MedicationExposure.medication_id == Medication.id)
        .where(MedicationExposure.user_id == user.id)
        .order_by(MedicationExposure.status, MedicationExposure.created_at.desc())
    )
    if active_only:
        stmt = stmt.where(MedicationExposure.status == "active")
    rows = db.execute(stmt).all()
    return [ExposureOut(**exposure_out(exposure, medication)) for exposure, medication in rows]


@router.post("", response_model=ExposureOut, status_code=status.HTTP_201_CREATED)
def add_medication(payload: ExposureCreate, user: CurrentUser, db: DbSession) -> ExposureOut:
    medication = resolve_medication(db, medication_id=payload.medication_id)
    if not medication:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown medication_id in the curated catalog.")
    duplicate = db.scalar(
        select(MedicationExposure).where(
            MedicationExposure.user_id == user.id,
            MedicationExposure.medication_id == medication.id,
            MedicationExposure.status == "active",
        )
    )
    if duplicate:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="This medication is already on your active list. Edit or stop the existing entry instead.",
        )
    exposure = MedicationExposure(
        user_id=user.id,
        medication_id=medication.id,
        dose_text=payload.dose_text,
        route=payload.route,
        frequency=payload.frequency,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status="active",
        reason=payload.reason,
        prescriber_specialty=payload.prescriber_specialty,
        notes=payload.notes,
        is_synthetic=False,
    )
    db.add(exposure)
    audit.record(
        db,
        user_id=user.id,
        action="medications.add",
        resource_type="medication_exposure",
        resource_id=exposure.id,
        detail={"medication_id": medication.id},
    )
    db.commit()
    db.refresh(exposure)
    return ExposureOut(**exposure_out(exposure, medication))


@router.patch("/{exposure_id}", response_model=ExposureOut)
def update_medication(
    exposure_id: str, payload: ExposureUpdate, user: CurrentUser, db: DbSession
) -> ExposureOut:
    row = db.execute(
        select(MedicationExposure, Medication)
        .join(Medication, MedicationExposure.medication_id == Medication.id)
        .where(MedicationExposure.id == exposure_id, MedicationExposure.user_id == user.id)
    ).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Medication entry not found.")
    exposure, medication = row
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if value is not None:
            setattr(exposure, key, value)
    audit.record(
        db,
        user_id=user.id,
        action="medications.update",
        resource_type="medication_exposure",
        resource_id=exposure.id,
        detail={"fields": sorted(data.keys())},
    )
    db.commit()
    db.refresh(exposure)
    return ExposureOut(**exposure_out(exposure, medication))


@router.delete("/{exposure_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_medication(exposure_id: str, user: CurrentUser, db: DbSession) -> None:
    exposure = db.scalar(
        select(MedicationExposure).where(
            MedicationExposure.id == exposure_id, MedicationExposure.user_id == user.id
        )
    )
    if not exposure:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Medication entry not found.")
    db.delete(exposure)
    audit.record(
        db, user_id=user.id, action="medications.delete", resource_type="medication_exposure", resource_id=exposure_id
    )
    db.commit()


@router.get("/interactions", response_model=list[InteractionOut])
def current_interactions(user: CurrentUser, db: DbSession) -> list[InteractionOut]:
    active = active_exposures(db, user.id)
    ids = {medication.id for _exposure, medication in active}
    rows = interactions_between(db, ids)
    return [
        InteractionOut(
            id=interaction.id,
            drug_a=drug_a.name,
            drug_b=drug_b.name,
            severity=interaction.severity,
            mechanism=interaction.mechanism,
            effect=interaction.effect,
            management=interaction.management,
            evidence_level=interaction.evidence_level,
            source_title=interaction.source_title,
            source_url=interaction.source_url,
        )
        for interaction, drug_a, drug_b in rows
    ]


@router.get("/{medication_id}", response_model=MedicationOut)
def medication_detail(medication_id: str, db: DbSession) -> MedicationOut:
    medication = resolve_medication(db, medication_id=medication_id)
    if not medication:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Medication not found.")
    return MedicationOut.model_validate(medication)
