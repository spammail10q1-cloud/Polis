from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import select

from app.core.security import CurrentUser, DbSession
from app.models import (
    GeneticSample,
    HealthProfile,
    Simulation,
    UserConsent,
    WearableDevice,
    WearableMeasurement,
)
from app.services.insights import build_insights
from app.services.labs import _aware, build_trends, latest_by_code, serialize_lab
from app.services.pgx import phenotype_map
from app.services.twin import build_overview, wearable_averages

router = APIRouter(prefix="/overview", tags=["overview"])

KEY_TREND_CODES = ["alt", "ldl", "hba1c", "egfr", "hs_crp", "vitamin_d"]
KEY_WEARABLE_METRICS = ["resting_hr", "hrv", "sleep_duration", "steps", "respiratory_rate"]


@router.get("")
def overview(user: CurrentUser, db: DbSession) -> dict:
    profile = db.scalar(select(HealthProfile).where(HealthProfile.user_id == user.id))
    consent = db.scalar(select(UserConsent).where(UserConsent.user_id == user.id))
    twin = build_overview(db, user.id)
    insights = build_insights(db, user.id)
    labs = latest_by_code(db, user.id)
    trends = build_trends(db, user.id)
    avg = wearable_averages(db, user.id, days=14)
    devices = list(db.scalars(select(WearableDevice).where(WearableDevice.user_id == user.id)).all())
    latest_wearable = db.scalar(
        select(WearableMeasurement)
        .where(WearableMeasurement.user_id == user.id)
        .order_by(WearableMeasurement.recorded_at.desc())
        .limit(1)
    )
    simulations = list(
        db.scalars(
            select(Simulation)
            .where(Simulation.user_id == user.id)
            .order_by(Simulation.created_at.desc())
            .limit(3)
        ).all()
    )
    samples = list(db.scalars(select(GeneticSample).where(GeneticSample.user_id == user.id)).all())

    latest_labs = []
    for code, (result, biomarker) in labs.items():
        latest_labs.append(serialize_lab(result, biomarker).model_dump(mode="json"))
    latest_labs.sort(key=lambda row: (row["category"], row["name"]))

    trend_payload = []
    for trend in trends:
        if trend.code in KEY_TREND_CODES or len(trend.points) > 1:
            trend_payload.append(trend.model_dump(mode="json"))
    trend_payload.sort(key=lambda row: abs(row.get("percent_change") or 0), reverse=True)

    wearable_summary = []
    for metric in KEY_WEARABLE_METRICS:
        if metric in avg:
            entry = avg[metric]
            wearable_summary.append(
                {
                    "metric": metric,
                    "average_14d": entry["average"],
                    "latest": entry["latest"],
                    "unit": entry["unit"],
                    "quality": entry["quality"],
                    "samples": entry["count"],
                }
            )

    latest_lab_time = max((_aware(result.measured_at) for result, _ in labs.values()), default=None)
    synthetic = any(result.is_synthetic for result, _ in labs.values()) or (profile.is_synthetic if profile else False)
    condition_names = [condition.get("name") for condition in (profile.conditions if profile else []) if condition.get("name")]
    age = None
    if profile and profile.date_of_birth:
        try:
            dob = datetime.strptime(profile.date_of_birth, "%Y-%m-%d")
            age = (datetime.now(UTC).date() - dob.date()).days // 365
        except ValueError:
            age = None

    from app.services.drugs import active_exposures

    active = active_exposures(db, user.id)
    pgx = phenotype_map(db, user.id)
    active_ids = {medication.id for _exposure, medication in active}
    suggestions = []
    if "CYP2C19" in pgx or "omeprazole" in active_ids or "clopidogrel" in active_ids:
        suggestions.append(
            {
                "medication_id": "clopidogrel",
                "label": "Clopidogrel",
                "reason": (
                    "CYP2C19 intermediate metabolizer and omeprazole interaction context"
                    if pgx.get("CYP2C19", {}).get("phenotype") == "Intermediate metabolizer"
                    else "CYP2C19 and antiplatelet interaction context"
                ),
            }
        )
    if "SLCO1B1" in pgx or "simvastatin" in active_ids:
        suggestions.append(
            {
                "medication_id": "simvastatin",
                "label": "Simvastatin",
                "reason": "SLCO1B1 transporter and statin exposure context",
            }
        )
    if "CYP2D6" in pgx or "metoprolol" in active_ids:
        suggestions.append(
            {
                "medication_id": "metoprolol",
                "label": "Metoprolol",
                "reason": "CYP2D6 substrate and current medication context" if "metoprolol" in active_ids else "CYP2D6 metabolism context",
            }
        )
    active_meds = [
        {
            "id": exposure.id,
            "medication_id": medication.id,
            "name": medication.name,
            "dose_text": exposure.dose_text,
            "frequency": exposure.frequency,
            "drug_class": medication.drug_class,
            "is_synthetic": exposure.is_synthetic,
        }
        for exposure, medication in active
    ]

    return {
        "user": {
            "name": user.name,
            "is_demo": user.is_demo,
            "email": user.email,
        },
        "profile": {
            "age": age,
            "sex_at_birth": profile.sex_at_birth if profile else None,
            "height_cm": profile.height_cm if profile else None,
            "weight_kg": profile.weight_kg if profile else None,
            "blood_type": profile.blood_type if profile else None,
            "conditions": condition_names,
            "allergies": [allergy.get("substance") for allergy in (profile.allergies if profile else [])],
            "is_synthetic": synthetic,
        },
        "synthetic_notice": "Demonstration data. Not real patient information." if user.is_demo else None,
        "twin": twin.model_dump(mode="json"),
        "latest_labs": latest_labs,
        "trends": trend_payload,
        "wearables": {
            "devices": [
                {
                    "provider": device.provider,
                    "name": device.name,
                    "status": device.connection_status,
                    "is_synthetic": device.is_synthetic,
                }
                for device in devices
            ],
            "summary": wearable_summary,
            "last_sample": _aware(latest_wearable.recorded_at).isoformat() if latest_wearable else None,
        },
        "active_medications": active_meds,
        "insights": [insight.model_dump(mode="json") for insight in insights],
        "recent_simulations": [
            {
                "id": row.id,
                "medication_name": row.medication_name,
                "status": row.status,
                "created_at": row.created_at.isoformat(),
                "headline": (row.output_json or {}).get("headline"),
            }
            for row in simulations
        ],
        "data_status": {
            "last_laboratory": latest_lab_time.isoformat() if latest_lab_time else None,
            "last_wearable_sample": _aware(latest_wearable.recorded_at).isoformat() if latest_wearable else None,
            "wearable_ingestion": "synthetic sample data" if devices else "not connected",
            "genetic_source": (
                "synthetic curated panel" if any(sample.is_synthetic for sample in samples) else
                ("uploaded VCF (annotations only)" if samples else None)
            ),
            "data_completeness": twin.overall_completeness,
            "not_a_health_score": True,
        },
        "privacy": {
            "ai_processing": consent.ai_processing if consent else False,
            "research_participation": consent.research_participation if consent else False,
            "federated_learning": consent.federated_learning if consent else False,
        },
        "suggested_simulations": suggestions,
        "generated_at": datetime.now(UTC).isoformat(),
        "disclaimer": (
            "POLIS does not produce an overall health score or diagnosis. Observations are separately labelled with "
            "evidence and uncertainty. The demonstration profile is entirely synthetic."
        ),
    }
