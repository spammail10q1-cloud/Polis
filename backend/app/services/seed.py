"""Reference-data and demonstration-data seeding (idempotent)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.data import demo
from app.data.biology import KG_EDGES, KG_NODES, PATHWAYS, SYSTEMS
from app.models import (
    AuditLog,
    BiologicalPathway,
    BiologicalSystem,
    Biomarker,
    DrugInteraction,
    EvidenceSource,
    FederatedTrainingRound,
    GeneticSample,
    GeneticVariant,
    HealthProfile,
    KnowledgeGraphEdge,
    KnowledgeGraphNode,
    LabResult,
    Medication,
    MedicationExposure,
    ModelVersion,
    PharmacogenomicPhenotype,
    PrivacyBudget,
    User,
    UserConsent,
    WearableDevice,
    WearableMeasurement,
)
from app.services.drugs import load_catalog, load_interactions
from app.services.evidence import embed_text


def seed_reference_data(db: Session) -> None:
    for data in demo.biomarker_seed():
        record = db.get(Biomarker, data["id"])
        if record:
            for key, value in data.items():
                setattr(record, key, value)
        else:
            db.add(Biomarker(**data))

    for data in load_catalog():
        record = db.get(Medication, data["id"])
        payload = dict(data)
        if record:
            for key, value in payload.items():
                setattr(record, key, value)
        else:
            db.add(Medication(**payload))

    # Ensure catalog rows exist before interaction foreign keys are checked.
    db.flush()

    for data in load_interactions():
        interaction_id = f"ddi_{data['drug_a_id']}_{data['drug_b_id']}"
        record = db.get(DrugInteraction, interaction_id)
        payload = dict(data, id=interaction_id)
        if record:
            for key, value in payload.items():
                setattr(record, key, value)
        else:
            db.add(DrugInteraction(**payload))

    for system in SYSTEMS:
        payload = {
            "id": system["id"],
            "name": system["name"],
            "tagline": system["tagline"],
            "description": system["description"],
            "organs": system["organs"],
            "pathways": system["pathways"],
            "accent": system["accent"],
            "sort_order": system["sort_order"],
        }
        record = db.get(BiologicalSystem, system["id"])
        if record:
            for key, value in payload.items():
                setattr(record, key, value)
        else:
            db.add(BiologicalSystem(**payload))

    for pathway in PATHWAYS:
        record = db.get(BiologicalPathway, pathway["id"])
        if record:
            for key, value in pathway.items():
                setattr(record, key, value)
        else:
            db.add(BiologicalPathway(**pathway))

    for node_id, kind, label, description in KG_NODES:
        record = db.get(KnowledgeGraphNode, node_id)
        metadata = {"synthetic_reference": False, "curated_v0": True}
        if record:
            record.kind = kind
            record.label = label
            record.description = description
            record.metadata_json = metadata
        else:
            db.add(KnowledgeGraphNode(id=node_id, kind=kind, label=label, description=description, metadata_json=metadata))

    db.flush()
    for source_id, target_id, relation, level, source in KG_EDGES:
        edge_id = f"kg_{source_id.split(':', 1)[-1]}_{relation}_{target_id.split(':', 1)[-1]}"
        if not db.get(KnowledgeGraphEdge, edge_id):
            db.add(
                KnowledgeGraphEdge(
                    id=edge_id,
                    source_id=source_id,
                    target_id=target_id,
                    relation=relation,
                    evidence_level=level,
                    source=source,
                    provenance={"curated": True, "note": "Small starter graph; not a complete biological knowledge base."},
                )
            )

    corpus = json.loads(
        (Path(__file__).resolve().parents[1] / "data" / "evidence_corpus.json").read_text(encoding="utf-8")
    )
    for item in corpus:
        embedding = embed_text(f"{item['title']} {item['summary']} {item['content']} {' '.join(item['tags'])}")
        record = db.get(EvidenceSource, item["id"])
        payload = dict(item, embedding=embedding)
        if record:
            for key, value in payload.items():
                setattr(record, key, value)
        else:
            db.add(EvidenceSource(**payload))

    for item in demo.MODEL_VERSIONS:
        record = db.get(ModelVersion, item["id"])
        if record:
            for key, value in item.items():
                setattr(record, key, value)
        else:
            db.add(ModelVersion(**item))

    db.flush()


def seed_demo_user(db: Session) -> User:
    existing = db.scalar(select(User).where(User.email == settings.demo_email))
    if existing:
        existing.password_hash = hash_password(settings.demo_password)
        return existing

    user = User(
        email=settings.demo_email,
        password_hash=hash_password(settings.demo_password),
        name=settings.demo_name,
        role="demo",
        is_demo=True,
        is_active=True,
    )
    db.add(user)
    db.flush()

    now = datetime.now(UTC)
    consent = UserConsent(
        user_id=user.id,
        terms_accepted=True,
        ai_processing=True,
        research_participation=False,
        federated_learning=False,
        analytics=False,
        consented_at=now,
    )
    db.add(consent)
    profile = HealthProfile(user_id=user.id, is_synthetic=True, **demo.PROFILE)
    db.add(profile)

    sample = GeneticSample(
        user_id=user.id,
        is_synthetic=True,
        variant_count=len(demo.VARIANTS),
        **demo.GENETIC_SAMPLE,
    )
    db.add(sample)
    db.flush()

    for gene, rsid, chromosome, position, ref, alt, genotype, zygosity, star, consequence, evidence, interpretation in demo.VARIANTS:
        db.add(
            GeneticVariant(
                sample_id=sample.id,
                user_id=user.id,
                gene=gene,
                rsid=rsid,
                chromosome=chromosome,
                position=position,
                ref=ref,
                alt=alt,
                genotype=genotype,
                zygosity=zygosity,
                star_allele=star,
                consequence=consequence,
                interpretation=interpretation,
                evidence_level=evidence,
                source="POLIS synthetic curated panel",
                confidence=0.95,
                is_synthetic=True,
            )
        )

    for gene, diplotype, phenotype, score, guideline, interpretation, medications, limitations in demo.PHENOTYPES:
        db.add(
            PharmacogenomicPhenotype(
                user_id=user.id,
                sample_id=sample.id,
                gene=gene,
                diplotype=diplotype,
                phenotype=phenotype,
                activity_score=score,
                guideline=guideline,
                interpretation=interpretation,
                medications=medications,
                limitations=limitations,
                source="POLIS synthetic curated diplotype",
                evidence_level="Curated demonstration: CPIC/PharmVar terminology",
                is_synthetic=True,
            )
        )

    for code, value, ref_low, ref_high, offset, source, context in demo.LATEST:
        db.add(
            LabResult(
                user_id=user.id,
                biomarker_id=code,
                value=value,
                unit=next(b["canonical_unit"] for b in demo.biomarker_seed() if b["id"] == code),
                ref_low=ref_low,
                ref_high=ref_high,
                measured_at=demo.days_ago(offset),
                source=source,
                method="Synthetic laboratory assay",
                confidence=0.9,
                quality_status="demonstration",
                notes="Demonstration data. Not real patient information.",
                context=context,
                provenance={"generator": "POLIS synthetic demo v1", "notice": "Demonstration data. Not real patient information."},
                is_synthetic=True,
            )
        )
    for code, value, ref_low, ref_high, offset in demo.HISTORICAL:
        db.add(
            LabResult(
                user_id=user.id,
                biomarker_id=code,
                value=value,
                unit=next(b["canonical_unit"] for b in demo.biomarker_seed() if b["id"] == code),
                ref_low=ref_low,
                ref_high=ref_high,
                measured_at=demo.days_ago(offset),
                source="Meridian Reference Lab (synthetic)",
                method="Synthetic laboratory assay",
                confidence=0.9,
                quality_status="demonstration",
                notes="Demonstration data. Not real patient information.",
                context={"synthetic": True},
                provenance={"generator": "POLIS synthetic demo v1", "notice": "Demonstration data. Not real patient information."},
                is_synthetic=True,
            )
        )

    for medication_id, dose, route, frequency, start_offset, reason, specialty in demo.MEDICATIONS:
        db.add(
            MedicationExposure(
                user_id=user.id,
                medication_id=medication_id,
                dose_text=dose,
                route=route,
                frequency=frequency,
                start_date=(now.date() - timedelta(days=start_offset)).isoformat(),
                status="active",
                reason=reason,
                prescriber_specialty=specialty,
                notes="Demonstration data: synthetic medication list",
                is_synthetic=True,
            )
        )

    device = WearableDevice(
        user_id=user.id,
        provider="oura",
        name="Oura Ring: synthetic sample",
        connection_status="sample_data",
        last_synced_at=now,
        is_synthetic=True,
    )
    db.add(device)
    db.flush()
    for row in demo.wearable_series():
        db.add(
            WearableMeasurement(
                user_id=user.id,
                device_id=device.id,
                metric=row["metric"],
                value=row["value"],
                unit=row["unit"],
                recorded_at=row["recorded_at"],
                source="Oura sample import (synthetic)",
                quality=row["quality"],
                is_synthetic=True,
            )
        )

    db.add(
        PrivacyBudget(
            user_id=user.id,
            epsilon_spent=0.0,
            epsilon_limit=settings.federated_privacy_budget,
        )
    )
    db.add(
        AuditLog(
            user_id=user.id,
            action="demo.seeded",
            resource_type="demo_dataset",
            resource_id="polis-demo-v1",
            detail={"notice": "Demonstration data. Not real patient information.", "synthetic": True},
        )
    )
    db.flush()
    return user


def seed_all(db: Session) -> None:
    seed_reference_data(db)
    if settings.demo_seed:
        seed_demo_user(db)
    db.commit()
