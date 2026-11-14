"""Medication catalog access and curated drug-interaction lookup."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import DrugInteraction, Medication, MedicationExposure

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def load_catalog() -> list[dict]:
    return json.loads((DATA_DIR / "drug_catalog.json").read_text(encoding="utf-8"))


def load_interactions() -> list[dict]:
    return json.loads((DATA_DIR / "interactions.json").read_text(encoding="utf-8"))


def resolve_medication(db: Session, *, medication_id: str | None = None, name: str | None = None) -> Medication | None:
    if medication_id:
        return db.get(Medication, medication_id.strip().lower())
    if not name:
        return None
    cleaned = name.strip().lower()
    stmt = select(Medication).where(
        or_(
            Medication.id == cleaned,
            Medication.name.ilike(f"%{cleaned}%"),
            Medication.generic_name.ilike(f"%{cleaned}%"),
        )
    )
    candidates = list(db.scalars(stmt).all())
    if not candidates:
        return None
    candidates.sort(key=lambda med: (med.name.lower() != cleaned and med.generic_name.lower() != cleaned, len(med.name)))
    return candidates[0]


def search(db: Session, query: str | None = None, limit: int = 30) -> list[Medication]:
    stmt = select(Medication).order_by(Medication.name)
    if query:
        cleaned = query.strip()
        if cleaned:
            stmt = stmt.where(
                or_(
                    Medication.name.ilike(f"%{cleaned}%"),
                    Medication.generic_name.ilike(f"%{cleaned}%"),
                    Medication.drug_class.ilike(f"%{cleaned}%"),
                )
            )
    return list(db.scalars(stmt.limit(limit)).all())


def active_exposures(db: Session, user_id: str) -> list[tuple[MedicationExposure, Medication]]:
    rows = db.execute(
        select(MedicationExposure, Medication)
        .join(Medication, MedicationExposure.medication_id == Medication.id)
        .where(MedicationExposure.user_id == user_id, MedicationExposure.status == "active")
        .order_by(MedicationExposure.created_at)
    ).all()
    return [(exposure, medication) for exposure, medication in rows]


def exposure_out(exposure: MedicationExposure, medication: Medication) -> dict:
    return {
        "id": exposure.id,
        "medication_id": medication.id,
        "name": medication.name,
        "drug_class": medication.drug_class,
        "dose_text": exposure.dose_text,
        "route": exposure.route,
        "frequency": exposure.frequency,
        "start_date": exposure.start_date,
        "end_date": exposure.end_date,
        "status": exposure.status,
        "reason": exposure.reason,
        "prescriber_specialty": exposure.prescriber_specialty,
        "notes": exposure.notes,
        "is_synthetic": exposure.is_synthetic,
        "enzyme_pathways": medication.enzyme_pathways,
    }


def interactions_between(db: Session, drug_ids: set[str]) -> list[tuple[DrugInteraction, Medication, Medication]]:
    if len(drug_ids) < 2:
        return []
    interactions = db.scalars(select(DrugInteraction)).all()
    meds = {med.id: med for med in db.scalars(select(Medication)).all()}
    result: list[tuple[DrugInteraction, Medication, Medication]] = []
    for interaction in interactions:
        if {interaction.drug_a_id, interaction.drug_b_id}.issubset(drug_ids):
            drug_a = meds.get(interaction.drug_a_id)
            drug_b = meds.get(interaction.drug_b_id)
            if drug_a and drug_b:
                result.append((interaction, drug_a, drug_b))
    severity_order = {"contraindicated": 0, "major": 1, "moderate": 2, "minor": 3}
    result.sort(key=lambda item: severity_order.get(item[0].severity, 9))
    return result


def interaction_pairs_for_medication(db: Session, user_id: str, proposed_id: str) -> list[dict]:
    active = active_exposures(db, user_id)
    active_ids = {med.id for _exposure, med in active}
    all_ids = active_ids | {proposed_id}
    output = []
    for interaction, drug_a, drug_b in interactions_between(db, all_ids):
        if proposed_id not in {drug_a.id, drug_b.id}:
            continue
        other = drug_b if drug_a.id == proposed_id else drug_a
        effect = interaction.simulation_effect or {}
        applies_to_proposed = effect.get("affected_drug_id") == proposed_id
        output.append(
            {
                "id": interaction.id,
                "drug_a": drug_a.name,
                "drug_b": drug_b.name,
                "other_medication": other.name,
                "severity": interaction.severity,
                "mechanism": interaction.mechanism,
                "effect": interaction.effect,
                "management": interaction.management,
                "evidence_level": interaction.evidence_level,
                "source_title": interaction.source_title,
                "source_url": interaction.source_url,
                "applies_to_proposed_simulation": applies_to_proposed,
                "simulation_effect": effect if applies_to_proposed else {},
            }
        )
    return output
