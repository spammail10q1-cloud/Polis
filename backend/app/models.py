"""POLIS data model.

All patient-owned records carry ``user_id`` and are queried with tenant filters.
Reference/catalog tables (biomarkers, medications, evidence, knowledge graph)
are shared and read-only for users. JSON columns hold flexible provenance,
context and simulation payloads; typed columns hold anything used for querying
or safety-relevant classification.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from app.core.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:20]}"


class UTCDateTime(TypeDecorator):
    """Store timestamps consistently and always return timezone-aware UTC values.

    SQLite drops timezone information on read; without this decorator, a UTC
    timestamp would be misinterpreted as local time by the browser.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("usr"))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    role: Mapped[str] = mapped_column(String(24), default="member", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class UserConsent(Base, TimestampMixin):
    __tablename__ = "user_consents"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cns"))
    user_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    terms_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_processing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    research_participation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    federated_learning: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    analytics: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_version: Mapped[str] = mapped_column(String(32), default="2026-11-01", nullable=False)
    consented_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class HealthProfile(Base, TimestampMixin):
    __tablename__ = "health_profiles"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pro"))
    user_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    date_of_birth: Mapped[str | None] = mapped_column(String(10))
    sex_at_birth: Mapped[str | None] = mapped_column(String(32))
    gender_identity: Mapped[str | None] = mapped_column(String(64))
    height_cm: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    blood_type: Mapped[str | None] = mapped_column(String(8))
    ancestry_context: Mapped[str | None] = mapped_column(String(160))
    smoking_status: Mapped[str | None] = mapped_column(String(32))
    alcohol_units_per_week: Mapped[float | None] = mapped_column(Float)
    activity_level: Mapped[str | None] = mapped_column(String(32))
    pregnancy_status: Mapped[str | None] = mapped_column(String(48))
    conditions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    allergies: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    family_history: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class GeneticSample(Base, TimestampMixin):
    __tablename__ = "genetic_samples"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gsp"))
    user_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source: Mapped[str] = mapped_column(String(48), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255))
    genome_build: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), default="parsed", nullable=False)
    variant_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class GeneticVariant(Base, TimestampMixin):
    __tablename__ = "genetic_variants"
    __table_args__ = (Index("ix_variant_user_gene", "user_id", "gene"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("var"))
    sample_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("genetic_samples.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    gene: Mapped[str] = mapped_column(String(32), nullable=False)
    rsid: Mapped[str] = mapped_column(String(32), nullable=False)
    chromosome: Mapped[str | None] = mapped_column(String(8))
    position: Mapped[int | None] = mapped_column(Integer)
    ref: Mapped[str | None] = mapped_column(String(16))
    alt: Mapped[str | None] = mapped_column(String(16))
    genotype: Mapped[str] = mapped_column(String(32), nullable=False)
    zygosity: Mapped[str] = mapped_column(String(24), nullable=False)
    star_allele: Mapped[str | None] = mapped_column(String(24))
    consequence: Mapped[str | None] = mapped_column(String(255))
    interpretation: Mapped[str | None] = mapped_column(Text)
    evidence_level: Mapped[str] = mapped_column(String(32), default="supported")
    source: Mapped[str] = mapped_column(String(80), default="POLIS synthetic dataset")
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class PharmacogenomicPhenotype(Base, TimestampMixin):
    __tablename__ = "pharmacogenomic_phenotypes"
    __table_args__ = (UniqueConstraint("user_id", "gene", name="uq_pgx_user_gene"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pgx"))
    user_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sample_id: Mapped[str | None] = mapped_column(
        String(40), ForeignKey("genetic_samples.id", ondelete="CASCADE"), index=True
    )
    gene: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    diplotype: Mapped[str] = mapped_column(String(64), nullable=False)
    phenotype: Mapped[str] = mapped_column(String(64), nullable=False)
    activity_score: Mapped[float | None] = mapped_column(Float)
    evidence_level: Mapped[str] = mapped_column(String(48), default="CPIC guideline")
    guideline: Mapped[str | None] = mapped_column(String(255))
    interpretation: Mapped[str] = mapped_column(Text, nullable=False)
    medications: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    limitations: Mapped[str] = mapped_column(Text, nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[str] = mapped_column(String(160), default="Synthetic curated diplotype")


class Biomarker(Base, TimestampMixin):
    __tablename__ = "biomarkers"

    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    code: Mapped[str] = mapped_column(String(48), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(48), index=True, nullable=False)
    canonical_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    specimen: Mapped[str] = mapped_column(String(48), default="Blood", nullable=False)
    typical_ref_low: Mapped[float | None] = mapped_column(Float)
    typical_ref_high: Mapped[float | None] = mapped_column(Float)
    reference_note: Mapped[str] = mapped_column(String(255), default="Typical adult interval; lab-specific ranges prevail")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class LabResult(Base, TimestampMixin):
    __tablename__ = "lab_results"
    __table_args__ = (
        Index("ix_lab_user_biomarker_date", "user_id", "biomarker_id", "measured_at"),
        Index("ix_lab_user_date", "user_id", "measured_at"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lab"))
    user_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    biomarker_id: Mapped[str] = mapped_column(
        String(48), ForeignKey("biomarkers.id"), index=True, nullable=False
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    ref_low: Mapped[float | None] = mapped_column(Float)
    ref_high: Mapped[float | None] = mapped_column(Float)
    ref_text: Mapped[str | None] = mapped_column(String(120))
    measured_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    source: Mapped[str] = mapped_column(String(160), default="Self-entered", nullable=False)
    method: Mapped[str | None] = mapped_column(String(160))
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    quality_status: Mapped[str] = mapped_column(String(32), default="self_reported", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    context: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Medication(Base, TimestampMixin):
    __tablename__ = "medications"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    generic_name: Mapped[str] = mapped_column(String(160), nullable=False)
    drug_class: Mapped[str] = mapped_column(String(160), nullable=False)
    atc_code: Mapped[str | None] = mapped_column(String(16))
    mechanism_summary: Mapped[str] = mapped_column(Text, nullable=False)
    enzyme_pathways: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    transporter_pathways: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    half_life_hours: Mapped[float | None] = mapped_column(Float)
    route_options: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    renal_fraction: Mapped[float | None] = mapped_column(Float)
    simulation_model: Mapped[str] = mapped_column(String(32), default="oral_pk", nullable=False)
    simulation_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    warnings: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    is_simulation_eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    parameter_note: Mapped[str] = mapped_column(Text, default="", nullable=False)


class MedicationExposure(Base, TimestampMixin):
    __tablename__ = "medication_exposures"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("mex"))
    user_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    medication_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("medications.id"), index=True, nullable=False
    )
    dose_text: Mapped[str] = mapped_column(String(80), nullable=False)
    route: Mapped[str] = mapped_column(String(32), default="oral", nullable=False)
    frequency: Mapped[str] = mapped_column(String(64), default="daily", nullable=False)
    start_date: Mapped[str | None] = mapped_column(String(10))
    end_date: Mapped[str | None] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(24), default="active", nullable=False)
    reason: Mapped[str | None] = mapped_column(String(160))
    prescriber_specialty: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class DrugInteraction(Base, TimestampMixin):
    __tablename__ = "drug_interactions"
    __table_args__ = (
        UniqueConstraint("drug_a_id", "drug_b_id", name="uq_interaction_pair"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ddi"))
    drug_a_id: Mapped[str] = mapped_column(String(64), ForeignKey("medications.id"), nullable=False)
    drug_b_id: Mapped[str] = mapped_column(String(64), ForeignKey("medications.id"), nullable=False)
    severity: Mapped[str] = mapped_column(String(24), nullable=False)
    mechanism: Mapped[str] = mapped_column(Text, nullable=False)
    effect: Mapped[str] = mapped_column(Text, nullable=False)
    management: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_level: Mapped[str] = mapped_column(String(48), nullable=False)
    source_title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    simulation_effect: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class WearableDevice(Base, TimestampMixin):
    __tablename__ = "wearable_devices"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dev"))
    user_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(48), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    connection_status: Mapped[str] = mapped_column(String(32), default="sample_data", nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class WearableMeasurement(Base, TimestampMixin):
    __tablename__ = "wearable_measurements"
    __table_args__ = (
        Index("ix_wearable_user_metric_time", "user_id", "metric", "recorded_at"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("wm"))
    user_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    device_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("wearable_devices.id", ondelete="CASCADE"), index=True, nullable=False
    )
    metric: Mapped[str] = mapped_column(String(48), index=True, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    quality: Mapped[str] = mapped_column(String(24), default="device_estimate", nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class BiologicalSystem(Base):
    __tablename__ = "biological_systems"

    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    tagline: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    organs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    pathways: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    accent: Mapped[str] = mapped_column(String(16), default="cyan", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class BiologicalPathway(Base):
    __tablename__ = "biological_pathways"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    genes: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    organs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    evidence_level: Mapped[str] = mapped_column(String(48), default="established biology")
    source: Mapped[str] = mapped_column(String(300), default="", nullable=False)


class KnowledgeGraphNode(Base):
    __tablename__ = "kg_nodes"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)


class KnowledgeGraphEdge(Base):
    __tablename__ = "kg_edges"
    __table_args__ = (Index("ix_kg_edge_source_target", "source_id", "target_id"),)

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("kg_nodes.id", ondelete="CASCADE"), nullable=False
    )
    target_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("kg_nodes.id", ondelete="CASCADE"), nullable=False
    )
    relation: Mapped[str] = mapped_column(String(48), nullable=False)
    evidence_level: Mapped[str] = mapped_column(String(48), nullable=False)
    source: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class EvidenceSource(Base, TimestampMixin):
    __tablename__ = "evidence_sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    organization: Mapped[str] = mapped_column(String(160), nullable=False)
    url: Mapped[str] = mapped_column(String(600), nullable=False)
    published_at: Mapped[str | None] = mapped_column(String(24))
    version: Mapped[str | None] = mapped_column(String(32))
    evidence_level: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    source_type: Mapped[str] = mapped_column(String(48), default="guideline", nullable=False)
    embedding: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class ModelVersion(Base, TimestampMixin):
    __tablename__ = "model_versions"

    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    limitations: Mapped[str] = mapped_column(Text, nullable=False)
    validation_summary: Mapped[str] = mapped_column(Text, nullable=False)


class Simulation(Base, TimestampMixin):
    __tablename__ = "simulations"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sim"))
    user_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    medication_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("medications.id"))
    medication_name: Mapped[str] = mapped_column(String(160), nullable=False)
    dose_text: Mapped[str | None] = mapped_column(String(80))
    route: Mapped[str | None] = mapped_column(String(32))
    frequency: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="complete", nullable=False)
    engine_version: Mapped[str] = mapped_column(String(48), nullable=False)
    input_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    evidence_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class FederatedTrainingRound(Base, TimestampMixin):
    __tablename__ = "federated_training_rounds"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fdr"))
    user_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    participants: Mapped[int] = mapped_column(Integer, nullable=False)
    epsilon: Mapped[float] = mapped_column(Float, nullable=False)
    loss: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="simulated", nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class PrivacyBudget(Base, TimestampMixin):
    __tablename__ = "privacy_budgets"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pbg"))
    user_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    epsilon_spent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    epsilon_limit: Mapped[float] = mapped_column(Float, default=8.0, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_user_time", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("aud"))
    user_id: Mapped[str | None] = mapped_column(
        String(40), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(80))
    detail: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, nullable=False
    )
