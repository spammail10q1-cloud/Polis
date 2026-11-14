from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, func, select

from app.core.config import settings
from app.core.security import CurrentUser, DbSession, clear_session_cookie, verify_password
from app.models import (
    AuditLog,
    FederatedTrainingRound,
    GeneticSample,
    GeneticVariant,
    HealthProfile,
    LabResult,
    MedicationExposure,
    PharmacogenomicPhenotype,
    PrivacyBudget,
    Simulation,
    UserConsent,
    WearableDevice,
    WearableMeasurement,
)
from app.schemas import (
    AuditOut,
    ConsentOut,
    ConsentState,
    ConsentUpdate,
    DeleteRequest,
    FederatedRoundRequest,
    FederatedRoundResult,
)
from app.services import audit
from app.services.federated import run_demo_rounds

router = APIRouter(prefix="/privacy", tags=["privacy"])

RETENTION = (
    "Health records remain until you delete them or close your account. Audit entries record actions, not free-text "
    "health content, and are removed with the account. Exported files are generated on request and not retained by POLIS."
)
RIGHTS = [
    "Access and export your data as machine-readable JSON.",
    "Delete health data while keeping your account, or delete the entire account.",
    "Withdraw AI processing consent at any time; the assistant will stop answering.",
    "Opt in or out of research participation independently of product use.",
    "Opt in or out of federated-learning participation independently of research consent.",
    "Review an audit trail of account and data actions.",
]


def _count(db, model, user_id: str, column="user_id") -> int:
    field = getattr(model, column)
    return int(db.scalar(select(func.count()).select_from(model).where(field == user_id)) or 0)


def _state(db, user_id: str) -> ConsentState:
    consent = db.scalar(select(UserConsent).where(UserConsent.user_id == user_id))
    if not consent:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Consent record missing.")
    budget = db.scalar(select(PrivacyBudget).where(PrivacyBudget.user_id == user_id))
    rounds = list(
        db.scalars(
            select(FederatedTrainingRound)
            .where(FederatedTrainingRound.user_id == user_id)
            .order_by(FederatedTrainingRound.created_at.desc())
            .limit(20)
        ).all()
    )
    inventory = [
        {"resource": "Laboratory results", "count": _count(db, LabResult, user_id)},
        {"resource": "Genetic samples", "count": _count(db, GeneticSample, user_id)},
        {"resource": "Genetic variants", "count": _count(db, GeneticVariant, user_id)},
        {"resource": "Pharmacogenomic phenotypes", "count": _count(db, PharmacogenomicPhenotype, user_id)},
        {"resource": "Medication entries", "count": _count(db, MedicationExposure, user_id)},
        {"resource": "Wearable devices", "count": _count(db, WearableDevice, user_id)},
        {"resource": "Wearable measurements", "count": _count(db, WearableMeasurement, user_id)},
        {"resource": "Simulations", "count": _count(db, Simulation, user_id)},
        {"resource": "Federated demonstration rounds", "count": _count(db, FederatedTrainingRound, user_id)},
        {"resource": "Audit entries", "count": _count(db, AuditLog, user_id)},
    ]
    return ConsentState(
        consent=ConsentOut.model_validate(consent),
        data_inventory=inventory,
        privacy_budget={
            "epsilon_spent": round(budget.epsilon_spent, 3) if budget else 0.0,
            "epsilon_limit": budget.epsilon_limit if budget else settings.federated_privacy_budget,
            "label": "Demonstration privacy ledger, not a formal end-to-end DP guarantee",
        },
        federated_rounds=[
            {
                "id": row.id,
                "round": row.round_number,
                "participants": row.participants,
                "epsilon": row.epsilon,
                "loss": row.loss,
                "accuracy": row.accuracy,
                "status": row.status,
                "created_at": row.created_at.isoformat(),
            }
            for row in rounds
        ],
        retention=RETENTION,
        rights=RIGHTS,
    )


@router.get("/consent", response_model=ConsentState)
def get_consent(user: CurrentUser, db: DbSession) -> ConsentState:
    return _state(db, user.id)


@router.patch("/consent", response_model=ConsentState)
def update_consent(payload: ConsentUpdate, user: CurrentUser, db: DbSession) -> ConsentState:
    consent = db.scalar(select(UserConsent).where(UserConsent.user_id == user.id))
    if not consent:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Consent record missing.")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(consent, key, value)
    if data:
        consent.consented_at = datetime.now(UTC)
    audit.record(
        db,
        user_id=user.id,
        action="privacy.consent_update",
        resource_type="user_consent",
        resource_id=consent.id,
        detail={"fields": {key: value for key, value in data.items()}},
    )
    db.commit()
    db.refresh(consent)
    return _state(db, user.id)


@router.get("/audit", response_model=list[AuditOut])
def audit_log(user: CurrentUser, db: DbSession) -> list[AuditOut]:
    rows = db.scalars(
        select(AuditLog).where(AuditLog.user_id == user.id).order_by(AuditLog.created_at.desc()).limit(200)
    ).all()
    return [AuditOut.model_validate(row) for row in rows]


def _export_payload(db, user, consent) -> dict[str, Any]:
    profile = db.scalar(select(HealthProfile).where(HealthProfile.user_id == user.id))
    labs = db.scalars(select(LabResult).where(LabResult.user_id == user.id).order_by(LabResult.measured_at)).all()
    samples = db.scalars(select(GeneticSample).where(GeneticSample.user_id == user.id)).all()
    variants = db.scalars(select(GeneticVariant).where(GeneticVariant.user_id == user.id)).all()
    phenotypes = db.scalars(
        select(PharmacogenomicPhenotype).where(PharmacogenomicPhenotype.user_id == user.id)
    ).all()
    exposures = db.scalars(
        select(MedicationExposure).where(MedicationExposure.user_id == user.id)
    ).all()
    devices = db.scalars(select(WearableDevice).where(WearableDevice.user_id == user.id)).all()
    wearables = db.scalars(
        select(WearableMeasurement).where(WearableMeasurement.user_id == user.id)
    ).all()
    simulations = db.scalars(select(Simulation).where(Simulation.user_id == user.id)).all()
    rounds = db.scalars(
        select(FederatedTrainingRound).where(FederatedTrainingRound.user_id == user.id)
    ).all()
    budget = db.scalar(select(PrivacyBudget).where(PrivacyBudget.user_id == user.id))
    logs = db.scalars(select(AuditLog).where(AuditLog.user_id == user.id)).all()
    return {
        "export_metadata": {
            "generated_at": datetime.now(UTC).isoformat(),
            "format": "POLIS data export v1",
            "contains_synthetic_demo_data": user.is_demo,
            "notice": "Demonstration data. Not real patient information." if user.is_demo else "User-exported health data",
            "not_a_medical_record": True,
        },
        "account": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "is_demo": user.is_demo,
            "created_at": user.created_at.isoformat(),
        },
        "consents": ConsentOut.model_validate(consent).model_dump(mode="json"),
        "profile": {
            **{
                key: getattr(profile, key)
                for key in [
                    "date_of_birth",
                    "sex_at_birth",
                    "gender_identity",
                    "height_cm",
                    "weight_kg",
                    "blood_type",
                    "ancestry_context",
                    "smoking_status",
                    "alcohol_units_per_week",
                    "activity_level",
                    "pregnancy_status",
                    "conditions",
                    "allergies",
                    "family_history",
                    "notes",
                    "is_synthetic",
                    "updated_at",
                ]
            }
        }
        if profile
        else None,
        "laboratory_results": [
            {
                "id": row.id,
                "biomarker_id": row.biomarker_id,
                "value": row.value,
                "unit": row.unit,
                "ref_low": row.ref_low,
                "ref_high": row.ref_high,
                "ref_text": row.ref_text,
                "measured_at": row.measured_at.isoformat(),
                "source": row.source,
                "method": row.method,
                "confidence": row.confidence,
                "quality_status": row.quality_status,
                "provenance": row.provenance,
                "is_synthetic": row.is_synthetic,
            }
            for row in labs
        ],
        "genetic_samples": [
            {
                "id": row.id,
                "source": row.source,
                "file_name": row.file_name,
                "status": row.status,
                "is_synthetic": row.is_synthetic,
                "provenance": row.provenance,
            }
            for row in samples
        ],
        "genetic_variants": [
            {
                "gene": row.gene,
                "rsid": row.rsid,
                "genotype": row.genotype,
                "zygosity": row.zygosity,
                "star_allele": row.star_allele,
                "evidence_level": row.evidence_level,
                "is_synthetic": row.is_synthetic,
            }
            for row in variants
        ],
        "pharmacogenomic_phenotypes": [
            {
                "gene": row.gene,
                "diplotype": row.diplotype,
                "phenotype": row.phenotype,
                "evidence_level": row.evidence_level,
                "interpretation": row.interpretation,
                "limitations": row.limitations,
                "is_synthetic": row.is_synthetic,
            }
            for row in phenotypes
        ],
        "medication_entries": [
            {
                "medication_id": row.medication_id,
                "dose_text": row.dose_text,
                "route": row.route,
                "frequency": row.frequency,
                "status": row.status,
                "reason": row.reason,
                "is_synthetic": row.is_synthetic,
            }
            for row in exposures
        ],
        "wearable_devices": [
            {"provider": row.provider, "name": row.name, "connection_status": row.connection_status, "is_synthetic": row.is_synthetic}
            for row in devices
        ],
        "wearable_measurements": [
            {
                "metric": row.metric,
                "value": row.value,
                "unit": row.unit,
                "recorded_at": row.recorded_at.isoformat(),
                "quality": row.quality,
                "is_synthetic": row.is_synthetic,
            }
            for row in wearables
        ],
        "simulations": [
            {
                "id": row.id,
                "medication_name": row.medication_name,
                "status": row.status,
                "engine_version": row.engine_version,
                "created_at": row.created_at.isoformat(),
                "input": row.input_json,
                "output": row.output_json,
            }
            for row in simulations
        ],
        "federated_demonstration_rounds": [
            {
                "round": row.round_number,
                "participants": row.participants,
                "epsilon": row.epsilon,
                "loss": row.loss,
                "accuracy": row.accuracy,
                "status": row.status,
                "details": row.details,
                "created_at": row.created_at.isoformat(),
            }
            for row in rounds
        ],
        "privacy_budget": (
            {"epsilon_spent": budget.epsilon_spent, "epsilon_limit": budget.epsilon_limit}
            if budget
            else None
        ),
        "audit_log": [
            {
                "action": row.action,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "detail": row.detail,
                "created_at": row.created_at.isoformat(),
            }
            for row in logs
        ],
    }


@router.post("/export")
def export_data(user: CurrentUser, db: DbSession) -> Response:
    consent = db.scalar(select(UserConsent).where(UserConsent.user_id == user.id))
    if not consent:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Consent record missing.")
    payload = _export_payload(db, user, consent)
    audit.record(db, user_id=user.id, action="privacy.export", resource_type="account", detail={"format": "json"})
    db.commit()
    filename = f"polis-export-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    content = json.dumps(jsonable_encoder(payload), indent=2, ensure_ascii=False).encode("utf-8")
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/data")
@router.delete("/data")
def delete_data(payload: DeleteRequest, user: CurrentUser, db: DbSession, response: Response) -> dict:
    if payload.confirmation.strip() != "DELETE MY DATA":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Type exactly "DELETE MY DATA" to confirm.')
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Password verification failed.")
    if user.is_demo:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="The shared demonstration account cannot be deleted. Create your own account to manage deletion.",
        )

    deleted_counts: dict[str, int] = {}
    if payload.scope == "account":
        audit.record(
            db,
            user_id=user.id,
            action="privacy.delete_account",
            resource_type="account",
            detail={"scope": "account"},
        )
        db.delete(user)
        db.commit()
        clear_session_cookie(response)
        return {
            "ok": True,
            "scope": "account",
            "message": "Account and all associated records were deleted.",
            "deleted_counts": deleted_counts,
        }

    for model, label, column in [
        (Simulation, "simulations", "user_id"),
        (FederatedTrainingRound, "federated_rounds", "user_id"),
        (WearableMeasurement, "wearable_measurements", "user_id"),
        (WearableDevice, "wearable_devices", "user_id"),
        (MedicationExposure, "medication_exposures", "user_id"),
        (LabResult, "lab_results", "user_id"),
        (PharmacogenomicPhenotype, "pharmacogenomic_phenotypes", "user_id"),
        (GeneticVariant, "genetic_variants", "user_id"),
        (GeneticSample, "genetic_samples", "user_id"),
        (HealthProfile, "health_profiles", "user_id"),
    ]:
        count = int(
            db.scalar(select(func.count()).select_from(model).where(getattr(model, column) == user.id)) or 0
        )
        db.execute(delete(model).where(getattr(model, column) == user.id))
        deleted_counts[label] = count

    budget = db.scalar(select(PrivacyBudget).where(PrivacyBudget.user_id == user.id))
    if budget:
        budget.epsilon_spent = 0.0
    consent = db.scalar(select(UserConsent).where(UserConsent.user_id == user.id))
    if consent:
        consent.research_participation = False
        consent.federated_learning = False
        consent.analytics = False
        consent.consented_at = datetime.now(UTC)
    audit.record(
        db,
        user_id=user.id,
        action="privacy.delete_health_data",
        resource_type="account",
        detail={"scope": "health_data", "deleted_counts": deleted_counts},
    )
    db.commit()
    return {
        "ok": True,
        "scope": "health_data",
        "message": "Health records were deleted. Your account and consent settings remain.",
        "deleted_counts": deleted_counts,
    }


@router.get("/federated-rounds")
def federated_rounds(user: CurrentUser, db: DbSession) -> dict:
    rounds = list(
        db.scalars(
            select(FederatedTrainingRound)
            .where(FederatedTrainingRound.user_id == user.id)
            .order_by(FederatedTrainingRound.round_number.desc())
        ).all()
    )
    budget = db.scalar(select(PrivacyBudget).where(PrivacyBudget.user_id == user.id))
    return {
        "rounds": [
            {
                "id": row.id,
                "round": row.round_number,
                "participants": row.participants,
                "epsilon": row.epsilon,
                "loss": row.loss,
                "accuracy": row.accuracy,
                "status": row.status,
                "details": row.details,
                "created_at": row.created_at.isoformat(),
            }
            for row in rounds
        ],
        "privacy_budget": {
            "epsilon_spent": round(budget.epsilon_spent, 3) if budget else 0.0,
            "epsilon_limit": budget.epsilon_limit if budget else settings.federated_privacy_budget,
        },
    }


@router.post("/federated-rounds", response_model=FederatedRoundResult)
def run_federated(payload: FederatedRoundRequest, user: CurrentUser, db: DbSession) -> FederatedRoundResult:
    consent = db.scalar(select(UserConsent).where(UserConsent.user_id == user.id))
    if not consent or not consent.federated_learning:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Federated-learning consent is not enabled. Enable the independent opt-in in Privacy & Data.",
        )
    result = run_demo_rounds(db, user, payload.rounds)
    audit.record(
        db,
        user_id=user.id,
        action="privacy.federated_demo",
        resource_type="federated_round",
        detail={"rounds": len(result["rounds"]), "epsilon_spent": result["epsilon_spent_total"]},
    )
    db.commit()
    return FederatedRoundResult(**result)
